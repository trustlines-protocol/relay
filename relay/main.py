import logging

from gevent.wsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from relay.relay import TrustlinesRelay
from relay.logger import get_logger
from .api.app import ApiApp


logger = get_logger('trustlines', logging.DEBUG)


def main():
    logger.info('Starting relay server')
    trustlines = TrustlinesRelay()
    trustlines.start()
    ipport = ('', 5000)
    app = ApiApp(trustlines)
    http_server = WSGIServer(ipport, app, log=None, handler_class=WebSocketHandler)
    logger.info('Server is running on {}'.format(ipport))
    http_server.serve_forever()


if __name__ == '__main__':
    main()
