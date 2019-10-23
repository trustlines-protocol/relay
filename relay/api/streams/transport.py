import logging

from geventwebsocket import WebSocketApplication, WebSocketError
from tinyrpc import BadRequestError

from relay.blockchain.events import Event, TLNetworkEvent
from relay.events import AccountEvent, MessageEvent
from relay.streams import Client, DisconnectedError, Subscription

from ..schemas import MessageEventSchema, UserCurrencyNetworkEventSchema
from .rpc_protocol import validating_rpc_caller

logger = logging.getLogger("websockets")


class RPCWebSocketApplication(WebSocketApplication):
    def __init__(self, rpc_protocol, dispatcher, ws):
        super().__init__(ws)
        self.rpc = rpc_protocol
        self.dispatcher = dispatcher
        self.client = RPCWebSocketClient(self.ws, self.rpc)

    def on_open(self):
        logger.debug("Websocket connected")

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
        logger.debug("Websocket disconnected")
        self.client.close()


class RPCWebSocketClient(Client):
    def __init__(self, ws, rpc_protocol):
        super().__init__()
        self.ws = ws
        self.rpc = rpc_protocol

    def _execute_send(self, subscription: Subscription, event: Event) -> None:
        if isinstance(event, TLNetworkEvent) or isinstance(event, AccountEvent):
            data = UserCurrencyNetworkEventSchema().dump(event)
        elif isinstance(event, MessageEvent):
            data = MessageEventSchema().dump(event)
        else:
            logger.warning("Could not sent event of type: %s", type(event))
            return
        assert isinstance(data, dict)
        request = self.rpc.create_request(
            "subscription_" + str(subscription.id), args={"event": data}, one_way=True
        )
        try:
            self.ws.send(request.serialize())
        except WebSocketError as e:
            raise DisconnectedError from e
