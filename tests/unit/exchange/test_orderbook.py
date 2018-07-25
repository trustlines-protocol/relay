import pytest

from relay.exchange.orderbook import OrderBook, OrderInvalidException
from relay.blockchain.exchange_proxy import DummyExchangeProxy
from relay.exchange.order import Order


@pytest.fixture()
def orderbook():
    return OrderBook()


def test_invalid_signature_order(orderbook: OrderBook, invalid_signature_order: Order):
    orderbook.add_exchange(DummyExchangeProxy(invalid_signature_order.exchange_address))
    assert not orderbook.validate(invalid_signature_order)
    with pytest.raises(OrderInvalidException):
        orderbook.add_order(invalid_signature_order)


def test_invalid_exchange_order(orderbook: OrderBook, valid_order: Order):
    assert not orderbook.validate(valid_order)
    with pytest.raises(OrderInvalidException):
        orderbook.add_order(valid_order)


def test_invalid_taker_order(orderbook: OrderBook, invalid_taker_order: Order):
    orderbook.add_exchange(DummyExchangeProxy(invalid_taker_order.exchange_address))
    assert not orderbook.validate(invalid_taker_order)
    with pytest.raises(OrderInvalidException):
        orderbook.add_order(invalid_taker_order)


def test_expired_order(orderbook: OrderBook, expired_order: Order):
    orderbook.add_exchange(DummyExchangeProxy(expired_order.exchange_address))
    assert not orderbook.validate(expired_order)
    with pytest.raises(OrderInvalidException):
        orderbook.add_order(expired_order)


def test_valid_order(orderbook: OrderBook, valid_order: Order):
    orderbook.add_exchange(DummyExchangeProxy(valid_order.exchange_address))
    assert orderbook.validate(valid_order)
    orderbook.add_order(valid_order)
