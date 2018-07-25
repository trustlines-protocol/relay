from functools import partial

from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol

from .rpc_methods import subscribe, messaging_subscribe, get_missed_messages
from .transport import RPCWebSocketApplication
from relay.relay import TrustlinesRelay


def WebSocketRPCHandler(trustlines: TrustlinesRelay):

    dispatcher = RPCDispatcher()
    dispatcher.add_method(partial(subscribe, trustlines), 'subscribe')

    protocol = JSONRPCProtocol()

    def handle(ws):
        app = RPCWebSocketApplication(protocol, dispatcher, ws)
        app.handle()
    return handle


def MessagingWebSocketRPCHandler(trustlines: TrustlinesRelay):

    dispatcher = RPCDispatcher()
    dispatcher.add_method(partial(messaging_subscribe, trustlines), 'listen')
    dispatcher.add_method(partial(get_missed_messages, trustlines), 'getMissedMessages')

    protocol = JSONRPCProtocol()

    def handle(ws):
        app = RPCWebSocketApplication(protocol, dispatcher, ws)
        app.handle()
    return handle
