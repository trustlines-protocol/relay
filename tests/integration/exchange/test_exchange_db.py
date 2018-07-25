from typing import Sequence

import pytest

from relay.exchange.order import Order
from relay.exchange.exchange_db import OrderBookDB


@pytest.fixture()
def orderbook_db(engine) -> OrderBookDB:
    return OrderBookDB(engine)


def test_get_order(order: Order, orderbook_db: OrderBookDB):

    orderbook_db.add_order(order)

    assert orderbook_db.get_order_by_hash(order.hash()) == order


def test_get_orders(orders: Sequence[Order], orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses

    orderbook_db.add_orders(orders)

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D))

    assert len(orders_result) == 3


def test_same_order_not_added(order: Order, orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses

    orderbook_db.add_order(order)
    orderbook_db.add_order(order)

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D))

    assert len(orders_result) == 1


def test_get_orders_order(orders: Sequence[Order], orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook_db.add_orders(orders)

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D))

    assert list(orders_result) == [o5, o1, o2]


def test_get_orders_order_price_desc(orders: Sequence[Order], orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook_db.add_orders(orders)

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D), desc_price=True)

    assert list(orders_result) == [o1, o2, o5]


def test_delete_order(orders: Sequence[Order], orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook_db.add_orders(orders)
    orderbook_db.delete_order_by_hash(o2.hash())

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D))

    assert list(orders_result) == [o5, o1]


def test_delete_orders(orders: Sequence[Order], orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook_db.add_orders(orders)
    orderbook_db.delete_orders_by_hash([o2.hash(), o5.hash()])

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D))

    assert list(orders_result) == [o1]


def test_delete_old_orders(orders: Sequence[Order], orderbook_db: OrderBookDB, addresses: Sequence[str]):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook_db.add_orders(orders)
    orderbook_db.delete_old_orders(1231000000000)

    orders_result = orderbook_db.get_orderbook_by_tokenpair((C, D))

    assert list(orders_result) == [o5, o2]
