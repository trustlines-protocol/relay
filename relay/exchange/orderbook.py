import time
from typing import Tuple, Sequence, Iterable

import gevent
import hexbytes

from relay.blockchain.exchange_proxy import ExchangeProxy
from relay.constants import NULL_ADDRESS
from .exchange_db import OrderBookDB
from .order import Order

UPDATE_INTERVAL = 60  # seconds


class OrderInvalidException(Exception):
    pass


class OrderBook(object):

    def __init__(self):
        self._db = None
        self._exchange_proxies = {}

    @property
    def exchange_addresses(self) -> Iterable[str]:
        return self._exchange_proxies.keys()

    def connect_db(self, engine):
        self._db = OrderBookDB(engine)

    def add_exchange(self, exchange_proxy):
        self._exchange_proxies[exchange_proxy.address] = exchange_proxy

    def validate(self, order: Order) -> bool:
        return (order.validate() and
                self.validate_exchange_address(order) and
                order.taker_address == NULL_ADDRESS and
                order.fee_recipient == NULL_ADDRESS and
                self.validate_timestamp(order) and
                self._exchange_proxies[order.exchange_address].validate(order))

    def validate_exchange_address(self, order: Order) -> bool:
        return order.exchange_address in self._exchange_proxies.keys()

    def validate_timestamp(self, order: Order) -> bool:
        return not order.is_expired(current_timestamp_in_sec=int(time.time()))

    def add_order(self, order: Order) -> None:
        if not self.validate(order):
            raise OrderInvalidException
        if self._db is not None:
            self._db.add_order(order)

    def add_orders(self, orders: Sequence[Order]) -> None:
        for order in orders:
            if not self.validate(order):
                raise OrderInvalidException
        if self._db is not None:
            self._db.add_orders(orders)

    def delete_order(self, order: Order) -> None:
        self.delete_order_by_hash(order.hash())

    def delete_order_by_hash(self, order_hash: hexbytes.HexBytes) -> None:
        if self._db is not None:
            self._db.delete_order_by_hash(order_hash)

    def delete_old_orders(self) -> None:
        if self._db is not None:
            self._db.delete_old_orders(timestamp=time.time())

    def get_asks_by_tokenpair(self, token_pair: Tuple[str, str]) -> Sequence[Order]:
        if self._db is not None:
            return self._db.get_orderbook_by_tokenpair(token_pair, desc_price=False)
        return []

    def get_bids_by_tokenpair(self, token_pair: Tuple[str, str]) -> Sequence[Order]:
        if self._db is not None:
            return self._db.get_orderbook_by_tokenpair(tuple(reversed(token_pair)), desc_price=True)
        return []

    def order_filled(self,
                     orderhash: bytes,
                     filled_maker_amount: int,
                     filled_taker_amount: int) -> None:
        if self._db is not None:
            return self._db.order_filled(orderhash, filled_maker_amount, filled_taker_amount)

    def get_orders(self,
                   filter_exchange_address,
                   filter_token_address,
                   filter_maker_token_address,
                   filter_taker_token_address,
                   filter_trader_address,
                   filter_maker_address,
                   filter_taker_address,
                   filter_fee_recipient_address) -> Sequence[Order]:
        if self._db is not None:
            return self._db.get_orders(filter_exchange_address,
                                       filter_token_address,
                                       filter_maker_token_address,
                                       filter_taker_token_address,
                                       filter_trader_address,
                                       filter_maker_address,
                                       filter_taker_address,
                                       filter_fee_recipient_address)
        return []

    def order_cancelled(self,
                        orderhash: hexbytes.HexBytes,
                        cancelled_maker_amount: int,
                        cancelled_taker_amount: int) -> None:
        if self._db is not None:
            return self._db.order_cancelled(orderhash, cancelled_maker_amount, cancelled_taker_amount)

    def get_order_by_hash(self, order_hash: hexbytes.HexBytes):
        if self._db is not None:
            return self._db.get_order_by_hash(order_hash)


class OrderBookGreenlet(OrderBook):

    def __init__(self):
        super().__init__()
        self.running = False

    def start(self):
        self.running = True
        for exchange_address in self.exchange_addresses:
            self._start_listen_on_fill_or_cancel(exchange_address)
        gevent.Greenlet.spawn(self._run)

    def add_exchange(self, exchange_proxy: ExchangeProxy):
        super().add_exchange(exchange_proxy)
        if self.running:
            self._start_listen_on_fill_or_cancel(exchange_proxy.address)

    def _start_listen_on_fill_or_cancel(self, exchange_address: str):
        self._exchange_proxies[exchange_address].start_listen_on_fill(self._db.order_filled)
        self._exchange_proxies[exchange_address].start_listen_on_cancel(self._db.order_cancelled)

    def _run(self):
        while self.running:
            self.delete_old_orders()
            gevent.sleep(UPDATE_INTERVAL)
