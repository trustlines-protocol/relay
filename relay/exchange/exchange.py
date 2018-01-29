import time
from typing import Tuple, Sequence


from ..constants import NULL_ADDRESS
from .exchange_db import OrderBookDB
from .order import Order


class OrderInvalidException(Exception):
    pass


class OrderBook(object):

    def __init__(self):
        self.exchange_addresses = []
        self._db = None

    def connect_db(self, engine):
        self._db = OrderBookDB(engine)

    def add_exchange_address(self, address: str):
        self.exchange_addresses.append(address)

    def validate(self, order: Order) -> bool:
        return (order.validate() and
                order.exchange_address in self.exchange_addresses and
                order.taker_address == NULL_ADDRESS and
                order.fee_recipient == NULL_ADDRESS and
                not order.is_expired(current_timestamp_in_sec=time.time()))

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

    def delete_order_by_hash(self, order_hash: bytes) -> None:
        if self._db is not None:
            self._db.delete_order_by_hash(order_hash)

    def delete_old_orders(self) -> None:
        if self._db is not None:
            self._db.delete_old_orders(self, timestamp=time.time())

    def get_asks_by_tokenpair(self, token_pair: Tuple[str, str]) -> Sequence[Order]:
        if self._db is not None:
            return self._db.get_orderbook_by_tokenpair(token_pair, desc_price=False)
        return []

    def get_bids_by_tokenpair(self, token_pair: Tuple[str, str]) -> Sequence[Order]:
        if self._db is not None:
            return self._db.get_orderbook_by_tokenpair(tuple(reversed(token_pair)), desc_price=True)
        return []
