import logging
import logging.config
import sys

import click
import sentry_sdk.integrations.flask
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from relay.api.app import ApiType
from relay.config.config import ValidationError, load_config, validation_error_string
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
    """handle --version argument

    we need this function, because otherwise click may check that the default
    --config or --addresses arguments are really files and they may not
    exist"""
    if value:
        click.echo(get_version())
        ctx.exit()


@click.command()
@click.option("--port", default=None, help="port to listen on [default: 5000]")
@click.option(
    "--config",
    default="config.toml",
    help="path to toml configuration file",
    show_default=True,
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--addresses",
    default=None,
    help="path to addresses json file",
    type=click.Path(exists=True, dir_okay=False),
)
@click.option(
    "--version",
    help="Prints the version of the software",
    is_flag=True,
    callback=_show_version,
)
@click.pass_context
def main(ctx, port: int, config: str, addresses: str, version) -> None:
    """run the relay server"""

    # silence warnings from urllib3, see github issue 246
    logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)

    logger.info("Starting relay server version %s", get_version())

    try:
        config_dict = load_config(config)
    except ValidationError as error:
        logger.error("Validation error in config: " + validation_error_string(error))
        sys.exit(1)
    configure_logging(config_dict)
    sentry_config = config_dict.get("sentry", None)
    if sentry_config is not None:
        sentry_sdk.init(
            dsn=sentry_config["dsn"],
            integrations=[sentry_sdk.integrations.flask.FlaskIntegration()],
        )

    if addresses is None:
        addresses = config_dict["relay"]["addresses_filepath"]
    trustlines = TrustlinesRelay(config=config_dict, addresses_json_path=addresses)
    trustlines.start()

    rest_config = config_dict["rest"]
    if port is None:
        port = rest_config["port"]
    host = rest_config["host"]
    ipport = (host, port)
    app = ApiApp(trustlines, enabled_apis=select_enabled_apis(config_dict))
    http_server = WSGIServer(ipport, app, log=None, handler_class=WebSocketHandler)
    logger.info("Server is running on {}".format(ipport))
    http_server.serve_forever()


def select_enabled_apis(config_dict):
    enabled_apis = []

    feature_to_apis = {
        "faucet": [ApiType.FAUCET],
        "delegate": [ApiType.DELEGATE],
        "trustline_index": [ApiType.STATUS, ApiType.PATHFINDING],
        "messaging": [ApiType.MESSAGING],
        "exchange": [ApiType.EXCHANGE],
        "tx_relay": [ApiType.RELAY],
        "push_notification": [ApiType.PUSH_NOTIFICATION],
    }

    for config_key, apis in feature_to_apis.items():
        if config_dict[config_key]["enable"]:
            enabled_apis.extend(apis)

    return enabled_apis
