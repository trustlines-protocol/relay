from relay.blockchain.unw_eth_proxy import UnwEthProxy
from relay.blockchain.token_proxy import TokenProxy

from relay.api.schemas import TokenEventSchema, UserTokenEventSchema
from flask_restful import Resource
from flask import abort
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate
from typing import Union  # noqa: F401
from relay.relay import TrustlinesRelay


def abort_if_unknown_token(trustlines, token_address):
    if token_address not in trustlines.token_addresses and token_address not in trustlines.unw_eth_addresses:
        abort(404, 'Unknown network: {}'.format(token_address))


class TokenAddresses(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.token_addresses


class TokenBalance(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, token_address: str, user_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        if token_address in self.trustlines.unw_eth_addresses:
            return str(self.trustlines.unw_eth_proxies[token_address].balance_of(user_address))
        else:
            return str(self.trustlines.token_proxies[token_address].balance_of(user_address))


class UserEventsToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(UnwEthProxy.event_types + TokenProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, token_address: str, user_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        from_block = args['fromBlock']
        type = args['type']

        if token_address in self.trustlines.unw_eth_addresses:
            proxy = self.trustlines.unw_eth_proxies[token_address]  # type: Union[UnwEthProxy, TokenProxy]
            func_names = ['get_unw_eth_events', 'get_all_unw_eth_events']
        else:
            proxy = self.trustlines.token_proxies[token_address]
            func_names = ['get_token_events', 'get_all_token_events']

        if type is not None:
            events = getattr(proxy, func_names[0])(type, user_address, from_block=from_block)
        else:
            events = getattr(proxy, func_names[1])(user_address, from_block=from_block)

        return UserTokenEventSchema().dump(events, many=True).data


class EventsToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(UnwEthProxy.event_types + TokenProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, token_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        from_block = args['fromBlock']
        type = args['type']

        if token_address in self.trustlines.unw_eth_addresses:
            proxy = self.trustlines.unw_eth_proxies[token_address]  # type: Union[UnwEthProxy, TokenProxy]
        else:
            proxy = self.trustlines.token_proxies[token_address]

        if type is not None:
            events = proxy.get_events(type, from_block=from_block)
        else:
            events = proxy.get_all_events(from_block=from_block)

        return TokenEventSchema().dump(events, many=True).data
