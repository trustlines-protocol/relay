import pytest

from relay.exchange.orderbook import OrderBook
from relay.blockchain.exchange_proxy import DummyExchangeProxy


@pytest.fixture()
def orderbook(engine, addresses):
    orderbook = OrderBook()
    orderbook.connect_db(engine)
    A, *rest = addresses
    orderbook.add_exchange(DummyExchangeProxy(A))
    return orderbook


def test_bids(orderbook: OrderBook, orders, addresses):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook.add_orders(orders)

    assert orderbook.get_bids_by_tokenpair((C, D)) == [o4]


def test_asks(orderbook: OrderBook, orders, addresses):
    A, B, C, D = addresses
    o1, o2, o3, o4, o5 = orders

    orderbook.add_orders(orders)

    assert orderbook.get_asks_by_tokenpair((C, D)) == [o5, o1, o2]
