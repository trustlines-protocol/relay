import logging
from flask_restful import Resource
from webargs.flaskparser import use_args
from webargs import fields as webfields
from webargs.flaskparser import abort
from eth_utils import to_checksum_address, is_hex
from marshmallow import validate
from relay.relay import TrustlinesRelay
from relay.api import fields
from relay.exchange.order import Order
from relay.exchange.orderbook import OrderInvalidException
from relay.blockchain.exchange_proxy import ExchangeProxy
from relay.concurrency_utils import TimeoutException
from relay.logger import get_logger

from ..schemas import ExchangeEventSchema, UserExchangeEventSchema

logger = get_logger('api.resources', logging.DEBUG)

TIMEOUT_MESSAGE = 'The server could not handle the request in time'

def order_as_dict(order: Order):
    return {
        'exchangeContractAddress': order.exchange_address,
        'maker': order.maker_address,
        'taker': order.taker_address,
        'makerTokenAddress': order.maker_token,
        'takerTokenAddress': order.taker_token,
        'feeRecipient': order.fee_recipient,
        'makerTokenAmount': str(order.maker_token_amount),
        'takerTokenAmount': str(order.taker_token_amount),
        'filledMakerTokenAmount': str(order.filled_maker_token_amount),
        'filledTakerTokenAmount': str(order.filled_taker_token_amount),
        'cancelledMakerTokenAmount': str(order.cancelled_maker_token_amount),
        'cancelledTakerTokenAmount': str(order.cancelled_taker_token_amount),
        'availableMakerTokenAmount': str(order.available_maker_token_amount),
        'availableTakerTokenAmount': str(order.available_taker_token_amount),
        'makerFee': str(order.maker_fee),
        'takerFee': str(order.taker_fee),
        'expirationUnixTimestampSec': str(order.expiration_timestamp_in_sec),
        'salt': str(order.salt),
        'ecSignature': {
            'v': int(order.v),
            'r': '0x{:032X}'.format(int.from_bytes(order.r, 'big')),
            's': '0x{:032X}'.format(int.from_bytes(order.s, 'big'))
        }
    }


def abort_if_unknown_exchange(trustlines, exchange_address):
    if exchange_address not in list(trustlines.exchange_addresses):
        abort(404, 'Unkown exchange: {}'.format(exchange_address))

def abort_if_invalid_order_hash(order_hash):
    if not is_hex(order_hash) or len(order_hash[2:]) != 64:
        abort(404, message='Invalid order hash: {}'.format(order_hash))


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
            'bids': [order_as_dict(order) for order in
                     self.trustlines.orderbook.get_bids_by_tokenpair((base_token_address, quote_token_address))],
            'asks': [order_as_dict(order) for order in
                     self.trustlines.orderbook.get_asks_by_tokenpair((base_token_address, quote_token_address))],

        }


class OrderDetail(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, order_hash: str):
        abort_if_invalid_order_hash(order_hash)
        order = self.trustlines.orderbook.get_order_by_hash(bytes.fromhex(order_hash[2:]))
        if order is None:
            abort(404, message='Order does not exist')
        return order_as_dict(order)


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
    def get(self, args, exchange_address: str, user_address: str):
        abort_if_unknown_exchange(self.trustlines, exchange_address)
        proxy = self.trustlines.orderbook._exchange_proxies[exchange_address]
        from_block = args['fromBlock']
        type = args['type']
        try:
            if type is not None:
                events = proxy.get_exchange_events(type,
                                                   user_address,
                                                   from_block=from_block,
                                                   timeout=self.trustlines.event_query_timeout)
            else:
                events = proxy.get_all_exchange_events(user_address,
                                                       from_block=from_block,
                                                       timeout=self.trustlines.event_query_timeout)
        except TimeoutException:
            logger.warning(
                "User exchange events: event_name=%s user_address=%s from_block=%s. could not get events in time",
                type,
                user_address,
                from_block)
            abort(504, TIMEOUT_MESSAGE)
        return UserExchangeEventSchema().dump(events, many=True).data


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
    def get(self, args, exchange_address: str):
        abort_if_unknown_exchange(self.trustlines, exchange_address)
        proxy = self.trustlines.orderbook._exchange_proxies[exchange_address]
        from_block = args['fromBlock']
        type = args['type']
        try:
            if type is not None:
                events = proxy.get_events(type,
                                          from_block=from_block,
                                          timeout=self.trustlines.event_query_timeout)
            else:
                events = proxy.get_all_events(from_block=from_block,
                                              timeout=self.trustlines.event_query_timeout)
        except TimeoutException:
            logger.warning(
                "Exchange events: event_name=%s from_block=%s. could not get events in time",
                type,
                from_block)
            abort(504, TIMEOUT_MESSAGE)
        return ExchangeEventSchema().dump(events, many=True).data
