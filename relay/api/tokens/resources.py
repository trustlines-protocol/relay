from relay.api.resources import dump_result_with_schema
from relay.blockchain.unw_eth_proxy import UnwEthProxy
from relay.blockchain.token_proxy import TokenProxy

from relay.api.schemas import TokenEventSchema, UserTokenEventSchema
from flask_restful import Resource
from flask import abort
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate
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
    @dump_result_with_schema(UserTokenEventSchema(many=True))
    def get(self, args, token_address: str, user_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        from_block = args['fromBlock']
        type = args['type']

        return self.trustlines.get_user_token_events(token_address,
                                                     user_address,
                                                     type=type,
                                                     from_block=from_block)


class EventsToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(UnwEthProxy.event_types +
                                                   TokenProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    @dump_result_with_schema(TokenEventSchema(many=True))
    def get(self, args, token_address: str):
        abort_if_unknown_token(self.trustlines, token_address)
        from_block = args['fromBlock']
        type = args['type']

        return self.trustlines.get_token_events(token_address, type=type, from_block=from_block)
