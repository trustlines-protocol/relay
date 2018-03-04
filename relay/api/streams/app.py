from functools import partial

from tinyrpc.dispatch import RPCDispatcher
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol

from .rpc_methods import subscribe
from .transport import RPCWebSocketApplication


def WebSocketRPCHandler(trustlines):

    dispatcher = RPCDispatcher()
    dispatcher.add_method(partial(subscribe, trustlines), 'subscribe')

    protocol = JSONRPCProtocol()

    def handle(ws):
        app = RPCWebSocketApplication(protocol, dispatcher, ws)
        app.handle()
    return handle
