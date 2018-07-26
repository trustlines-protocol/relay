import logging

from geventwebsocket import WebSocketApplication, WebSocketError
from tinyrpc import BadRequestError

from relay.streams import Client, DisconnectedError
from .rpc_protocol import validating_rpc_caller
from ..schemas import UserCurrencyNetworkEventSchema
from relay.blockchain.events import Event
from relay.logger import get_logger

logger = get_logger('websockets', logging.DEBUG)


class RPCWebSocketApplication(WebSocketApplication):

    def __init__(self, rpc_protocol, dispatcher, ws):
        super().__init__(ws)
        self.rpc = rpc_protocol
        self.dispatcher = dispatcher
        self.client = RPCWebSocketClient(self.ws, self.rpc)

    def on_open(self):
        logger.debug('Websocket connected')

    def on_message(self, message):

        def caller(method, args, kwargs):
            return validating_rpc_caller(method, args, kwargs, client=self.client)

        try:
            request = self.rpc.parse_request(message)
        except BadRequestError as e:
            # request was invalid, directly create response
            response = e.error_respond()
        else:
            response = self.dispatcher.dispatch(request, caller=caller)

        # now send the response to the client
        if response is not None:
            try:
                self.ws.send(response.serialize())
            except WebSocketError:
                pass

    def on_close(self, reason):
        logger.debug('Websocket disconnected')
        self.client.close()


class RPCWebSocketClient(Client):

    def __init__(self, ws, rpc_protocol):
        super().__init__()
        self.ws = ws
        self.rpc = rpc_protocol

    def send(self, id, event):
        if isinstance(event, str) or isinstance(event, dict):
            event = event
        elif isinstance(event, Event):
            event = UserCurrencyNetworkEventSchema().dump(event).data
        else:
            raise ValueError('Unexpected Type: ' + type(event))
        request = self.rpc.create_request('subscription_' + str(id), args={'event': event}, one_way=True)
        try:
            self.ws.send(request.serialize())
        except WebSocketError as e:
            raise DisconnectedError from e
