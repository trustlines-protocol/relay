# Make external libs work with gevent, but still enable real threading
from gevent import monkey; monkey.patch_all(thread=False)  # noqa: E702
# Make postgresql usable with gevent
import psycogreen.gevent; psycogreen.gevent.patch_psycopg()  # noqa: E702
import logging

import pkg_resources
import click
from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from relay.relay import TrustlinesRelay
from relay.logger import get_logger
from .api.app import ApiApp


logger = get_logger('trustlines', logging.DEBUG)


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
        return orig_simplefilter(action, category=category, lineno=lineno, append=append)

    warnings.simplefilter = simplefilter
    logger.info("the warnings module has been patched. You will not see the DeprecationWarning messages from web3")


def get_version():
    try:
        return pkg_resources.get_distribution("trustlines-relay").version
    except pkg_resources.DistributionNotFound:
        return "<UNKNOWN>"


@click.command()
@click.option("--port", default=5000)
@click.option("--config", default="config.json", help="path to json configuration file")
@click.option("--addresses", default="addresses.json", help="path to addresses json file")
@click.option("--version", help="Prints the version of the software", is_flag=True)
@click.pass_context
def main(ctx, port, config, addresses, version):
    """run the relay server"""
    if version:
        click.echo(get_version())
        ctx.exit()
    logger.info('Starting relay server version %s', get_version())
    trustlines = TrustlinesRelay(config_json_path=config, addresses_json_path=addresses)
    trustlines.start()
    ipport = ('', port)
    app = ApiApp(trustlines)
    http_server = WSGIServer(ipport, app, log=None, handler_class=WebSocketHandler)
    logger.info('Server is running on {}'.format(ipport))
    http_server.serve_forever()


if __name__ == '__main__':
    main()
