from relay.blockchain.unw_eth_proxy import UnwEthProxy

from relay.api.schemas import TokenEventSchema, UserTokenEventSchema
from flask_restful import Resource
from flask import abort
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate
from relay.relay import TrustlinesRelay


def abort_if_unknown_token(trustlines, token_address):
    if token_address not in trustlines.tokens and token_address not in trustlines.unw_eth:
        abort(404, 'Unkown network: {}'.format(token_address))


class TokenAddresses(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.unw_eth + self.trustlines.tokens


class TokenBalance(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, token_address: str, user_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        if token_address in self.trustlines.unw_eth:
            return self.trustlines.unw_eth_proxies[token_address].balance_of(user_address)
        else:
            return self.trustlines.token_proxies[token_address].balance_of(user_address)


class UserEventsToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(UnwEthProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, token_address: str, user_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        from_block = args['fromBlock']
        type = args['type']

        if token_address in self.trustlines.unw_eth:
            unw_eth_proxy = self.trustlines.unw_eth_proxies[token_address]
            if type is not None:
                events = unw_eth_proxy.get_unw_eth_events(type, user_address, from_block=from_block)
            else:
                events = unw_eth_proxy.get_all_unw_eth_events(user_address, from_block=from_block)
        else:
            # TODO
            # token_proxy = self.trustlines.token_proxies[token_address]
            events = []
        return UserTokenEventSchema().dump(events, many=True).data


class EventsToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(UnwEthProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, token_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        from_block = args['fromBlock']
        type = args['type']

        if token_address in self.trustlines.unw_eth:
            unw_eth_proxy = self.trustlines.unw_eth_proxies[token_address]
            if type is not None:
                events = unw_eth_proxy.get_events(type, from_block=from_block)
            else:
                events = unw_eth_proxy.get_all_events(from_block=from_block)
        else:
            # TODO
            # token_proxy = self.trustlines.token_proxies[token_address]
            events = []
        return TokenEventSchema().dump(events, many=True).data
