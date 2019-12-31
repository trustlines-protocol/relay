# Make external libs work with gevent, but still enable real threading
from gevent import monkey  # isort:skip

monkey.patch_all(thread=False)  # noqa: E702 isort:skip
# Make postgresql usable with gevent
import psycogreen.gevent  # isort:skip

psycogreen.gevent.patch_psycopg()  # noqa: E702 isort:skip
import json
import logging
import logging.config
import os

import click
import toml
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from relay.relay import TrustlinesRelay
from relay.utils import get_version

from .api.app import ApiApp

logger = logging.getLogger("trustlines")


def patch_warnings_module():
    """patch the warnings modules simplefilter function

    the web3 module prints excessive deprecation warnings. They call

      warnings.simplefilter('always', DeprecationWarning)

    in web3.utils.decorators before calling into warnings.warn. So, we need to
    take some drastic measures to prevent the flood of deprecation warnings
    cluttering all of our logs.

    We replace warnings.simplefilter with a function that does nothing when
    called with category=DeprecationWarning.
    """
    import warnings

    orig_simplefilter = warnings.simplefilter

    def simplefilter(action, category=Warning, lineno=0, append=False):
        if category is DeprecationWarning:
            return
        return orig_simplefilter(
            action, category=category, lineno=lineno, append=append
        )

    warnings.simplefilter = simplefilter
    logger.info(
        "the warnings module has been patched. You will not see the DeprecationWarning messages from web3"
    )


def configure_logging(config):
    """configure the logging subsystem via the 'logging' key in the TOML config"""
    try:
        logging_dict = {"version": 1, "incremental": True}
        logging_dict.update(config.get("logging", {}))
        logging.config.dictConfig(logging_dict)
    except (ValueError, TypeError, AttributeError, ImportError) as err:
        click.echo(
            f"Error configuring logging: {err}\n" "Please check your configuration file"
        )
        raise click.Abort()

    logger.debug(
        "Initialized logging system with the following config: %r", logging_dict
    )


def _show_version(ctx, param, value):
    """handle --version argumemt

    we need this function, because otherwise click may check that the default
    --config or --addresses arguments are really files and they may not
    exist"""
    if value:
        click.echo(get_version())
        ctx.exit()


@click.command()
@click.option("--port", default=5000, show_default=True, help="port to listen on")
@click.option(
    "--config",
    default="config.toml",
    help="path to toml configuration file",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--addresses",
    default="addresses.json",
    help="path to addresses json file",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--version",
    help="Prints the version of the software",
    is_flag=True,
    callback=_show_version,
)
@click.pass_context
def main(ctx, port, config, addresses, version):
    """run the relay server"""
    logging.basicConfig(
        format="%(asctime)s[%(levelname)s] %(name)s: %(message)s",
        level=os.environ.get("LOGLEVEL", "INFO").upper(),
    )

    # silence warnings from urllib3, see github issue 246
    logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)

    logger.info("Starting relay server version %s", get_version())

    # we still handle the json file for now. This will be removed
    # soon. But it's nice to see the end2end tests succeed.
    with open(config) as config_file:
        if config.lower().endswith(".json"):
            config_dict = {"relay": json.load(config_file)}
        else:
            config_dict = toml.load(config_file)
    configure_logging(config_dict)

    trustlines = TrustlinesRelay(
        config=config_dict["relay"], addresses_json_path=addresses
    )
    trustlines.start()
    ipport = ("", port)
    app = ApiApp(trustlines)
    http_server = WSGIServer(ipport, app, log=None, handler_class=WebSocketHandler)
    logger.info("Server is running on {}".format(ipport))
    http_server.serve_forever()


if __name__ == "__main__":
    main()
