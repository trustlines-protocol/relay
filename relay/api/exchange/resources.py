import logging

import hexbytes
from flask_restful import Resource
from webargs.flaskparser import use_args
from webargs import fields as webfields
from webargs.flaskparser import abort
from eth_utils import to_checksum_address, is_hex
from marshmallow import validate

from relay.api.resources import dump_result_with_schema
from relay.relay import TrustlinesRelay
from relay.api import fields
from relay.api.exchange.schemas import OrderSchema
from relay.exchange.order import Order
from relay.exchange.orderbook import OrderInvalidException
from relay.blockchain.exchange_proxy import ExchangeProxy
from relay.concurrency_utils import TimeoutException
from relay.logger import get_logger

from ..schemas import ExchangeEventSchema, UserExchangeEventSchema

logger = get_logger('api.resources', logging.DEBUG)

TIMEOUT_MESSAGE = 'The server could not handle the request in time'


def abort_if_invalid_order_hash(order_hash):
    if not is_hex(order_hash) or len(order_hash[2:]) != 64:
        abort(404, message='Invalid order hash: {}'.format(order_hash))


def abort_if_unknown_exchange(trustlines, exchange_address):
    if exchange_address not in trustlines.exchange_addresses and exchange_address not in trustlines.exchange_addresses:
        abort(404, 'Unknown exchange: {}'.format(exchange_address))


class OrderBook(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'baseTokenAddress': fields.Address(required=True),
        'quoteTokenAddress': fields.Address(required=True)
    }

    @use_args(args)
    def get(self, args):
        base_token_address = to_checksum_address(args['baseTokenAddress'])
        quote_token_address = to_checksum_address(args['quoteTokenAddress'])
        return {
            'bids': OrderSchema().dump(
                self.trustlines.orderbook.get_bids_by_tokenpair((base_token_address, quote_token_address)),
                many=True).data,
            'asks': OrderSchema().dump(
                self.trustlines.orderbook.get_asks_by_tokenpair((base_token_address, quote_token_address)),
                many=True).data,
        }


class OrderDetail(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(OrderSchema())
    def get(self, order_hash: str):
        abort_if_invalid_order_hash(order_hash)
        order = self.trustlines.orderbook.get_order_by_hash(hexbytes.HexBytes(order_hash))
        if order is None:
            abort(404, message='Order does not exist')
        return order


class Orders(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'exchangeContractAddress': fields.Address(required=False, missing=None),
        'tokenAddress': fields.Address(required=False, missing=None),
        'makerTokenAddress': fields.Address(required=False, missing=None),
        'takerTokenAddress': fields.Address(required=False, missing=None),
        'maker': fields.Address(required=False, missing=None),
        'taker': fields.Address(required=False, missing=None),
        'trader': fields.Address(required=False, missing=None),
        'feeRecipient': fields.Address(required=False, missing=None)
    }

    @use_args(args)
    @dump_result_with_schema(OrderSchema(many=True))
    def get(self, args):
        return self.trustlines.orderbook.get_orders(
            filter_exchange_address=args['exchangeContractAddress'],
            filter_token_address=args['tokenAddress'],
            filter_maker_token_address=args['makerTokenAddress'],
            filter_taker_token_address=args['takerTokenAddress'],
            filter_trader_address=args['maker'],
            filter_maker_address=args['taker'],
            filter_taker_address=args['trader'],
            filter_fee_recipient_address=args['feeRecipient'])


class OrderSubmission(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'exchangeContractAddress': fields.Address(required=True),
        'maker': fields.Address(required=True),
        'taker': fields.Address(required=True),
        'makerTokenAddress': fields.Address(required=True),
        'takerTokenAddress': fields.Address(required=True),
        'feeRecipient': fields.Address(required=True),
        'makerTokenAmount': fields.BigInteger(required=True),
        'takerTokenAmount': fields.BigInteger(required=True),
        'makerFee': fields.BigInteger(required=True),
        'takerFee': fields.BigInteger(required=True),
        'expirationUnixTimestampSec': fields.BigInteger(required=True),
        'salt': fields.BigInteger(required=True),
        'ecSignature': webfields.Nested({
            'v': webfields.Int(required=True),
            'r': fields.HexBytes(required=True),
            's': fields.HexBytes(required=True)
        }, required=True)
    }

    @use_args(args)
    def post(self, args):
        orderbook = self.trustlines.orderbook
        order = Order(exchange_address=args['exchangeContractAddress'],
                      maker_address=args['maker'],
                      taker_address=args['taker'],
                      maker_token=args['makerTokenAddress'],
                      taker_token=args['takerTokenAddress'],
                      fee_recipient=args['feeRecipient'],
                      maker_token_amount=args['makerTokenAmount'],
                      taker_token_amount=args['takerTokenAmount'],
                      maker_fee=args['makerFee'],
                      taker_fee=args['takerFee'],
                      expiration_timestamp_in_sec=args['expirationUnixTimestampSec'],
                      salt=args['salt'],
                      v=args['ecSignature']['v'],
                      r=args['ecSignature']['r'],
                      s=args['ecSignature']['s'])

        if not order.validate_signature():
            abort(422, message='Invalid ECDSA')

        if not orderbook.validate_exchange_address(order):
            abort(422, message='Invalid Exchange Address')

        if not orderbook.validate_timestamp(order):
            abort(422, message='Order already timed out')

        try:
            self.trustlines.orderbook.add_order(order)
        except OrderInvalidException:
            abort(422, message='Invalid Order')


class ExchangeAddresses(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return list(self.trustlines.exchange_addresses)


class UnwEthAddresses(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.unw_eth_addresses


class UserEventsExchange(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': webfields.Int(required=False, missing=0),
        'type': webfields.Str(required=False,
                              validate=validate.OneOf(ExchangeProxy.event_types),
                              missing=None)
    }

    @use_args(args)
    @dump_result_with_schema(UserExchangeEventSchema(many=True))
    def get(self, args, exchange_address: str, user_address: str):
        abort_if_unknown_exchange(self.trustlines, exchange_address)
        from_block = args['fromBlock']
        type = args['type']
        try:
            return self.trustlines.get_user_exchange_events(exchange_address,
                                                            user_address,
                                                            type=type,
                                                            from_block=from_block)
        except TimeoutException:
            logger.warning(
                "User exchange events: event_name=%s user_address=%s from_block=%s. could not get events in time",
                type,
                user_address,
                from_block)
            abort(504, TIMEOUT_MESSAGE)


class UserEventsAllExchanges(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': webfields.Int(required=False, missing=0),
        'type': webfields.Str(required=False,
                              validate=validate.OneOf(ExchangeProxy.event_types),
                              missing=None)
    }

    @use_args(args)
    @dump_result_with_schema(UserExchangeEventSchema(many=True))
    def get(self, args, user_address: str):
        from_block = args['fromBlock']
        type = args['type']
        try:
            return self.trustlines.get_all_user_exchange_events(user_address,
                                                                type=type,
                                                                from_block=from_block)
        except TimeoutException:
            logger.warning(
                """User exchange events from all exchanges:
                   event_name=%s user_address=%s from_block=%s. could not get events in time""",
                type,
                user_address,
                from_block)
            abort(504, TIMEOUT_MESSAGE)


class EventsExchange(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': webfields.Int(required=False, missing=0),
        'type': webfields.Str(required=False,
                              validate=validate.OneOf(ExchangeProxy.event_types),
                              missing=None)
    }

    @use_args(args)
    @dump_result_with_schema(ExchangeEventSchema(many=True))
    def get(self, args, exchange_address: str):
        abort_if_unknown_exchange(self.trustlines, exchange_address)
        from_block = args['fromBlock']
        type = args['type']
        try:
            return self.trustlines.get_exchange_events(exchange_address, type=type, from_block=from_block)
        except TimeoutException:
            logger.warning(
                "Exchange events: event_name=%s from_block=%s. could not get events in time",
                type,
                from_block)
            abort(504, TIMEOUT_MESSAGE)
