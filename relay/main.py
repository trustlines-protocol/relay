# Make external libs work with gevent, but still enable real threading
from gevent import monkey; monkey.patch_all(thread=False)  # noqa: E702
# Make postgresql usable with gevent
import psycogreen.gevent; psycogreen.gevent.patch_psycopg()  # noqa: E702
import logging

import pkg_resources
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


def main():
    logger.info('Starting relay server version %s', get_version())
    trustlines = TrustlinesRelay()
    trustlines.start()
    ipport = ('', 5000)
    app = ApiApp(trustlines)
    http_server = WSGIServer(ipport, app, log=None, handler_class=WebSocketHandler)
    logger.info('Server is running on {}'.format(ipport))
    http_server.serve_forever()


if __name__ == '__main__':
    main()
