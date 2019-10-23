from functools import partial

from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol

from relay.relay import TrustlinesRelay

from .rpc_methods import get_missed_messages, messaging_subscribe, subscribe
from .transport import RPCWebSocketApplication


def WebSocketRPCHandler(trustlines: TrustlinesRelay):

    dispatcher = RPCDispatcher()
    dispatcher.add_method(partial(subscribe, trustlines), "subscribe")

    protocol = JSONRPCProtocol()

    def handle(ws):
        app = RPCWebSocketApplication(protocol, dispatcher, ws)
        app.handle()

    return handle


def MessagingWebSocketRPCHandler(trustlines: TrustlinesRelay):

    dispatcher = RPCDispatcher()
    dispatcher.add_method(partial(messaging_subscribe, trustlines), "listen")
    dispatcher.add_method(partial(get_missed_messages, trustlines), "getMissedMessages")

    protocol = JSONRPCProtocol()

    def handle(ws):
        app = RPCWebSocketApplication(protocol, dispatcher, ws)
        app.handle()

    return handle
