import pytest
from sqlalchemy import create_engine

from relay.blockchain.exchange_proxy import ExchangeProxy
from relay.exchange.orderbook import OrderBookGreenlet


@pytest.fixture()
def engine():
    return create_engine('sqlite:///:memory:')


@pytest.fixture()
def orderBook(engine, web3, exchange_abi, token_abi, testnetworks, is_currency_network_function):
    exchange_address = testnetworks[1].address
    orderBook = OrderBookGreenlet()
    orderBook.connect_db(engine)

    orderBook.add_exchange(
        ExchangeProxy(
            web3,
            exchange_abi,
            token_abi,
            exchange_address,
            is_currency_network_function))

    return orderBook
