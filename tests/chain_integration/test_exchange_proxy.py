import gevent
import pytest

from relay.blockchain.exchange_proxy import ExchangeProxy
from relay.constants import NULL_ADDRESS
from relay.exchange.order import SignableOrder


@pytest.fixture()
def order_token(exchange_address, network_addresses_with_exchange, unw_eth_address, test_account):
    order = SignableOrder(
        exchange_address=exchange_address,
        maker_address=test_account.address,
        taker_address=NULL_ADDRESS,
        maker_token=unw_eth_address,
        taker_token=network_addresses_with_exchange[0],
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=1230000000000,
        salt=123
        )
    order.sign(test_account.private_key)
    return order


@pytest.fixture()
def order_trustlines(exchange_address, network_addresses_with_exchange, unw_eth_address, test_account):
    order = SignableOrder(
        exchange_address=exchange_address,
        maker_address=test_account.address,
        taker_address=NULL_ADDRESS,
        maker_token=network_addresses_with_exchange[0],
        taker_token=unw_eth_address,
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=1230000000000,
        salt=123
        )
    order.sign(test_account.private_key)
    return order


@pytest.fixture()
def exchange_proxy(web3, exchange_abi, token_abi, exchange_address, address_oracle):
    return ExchangeProxy(
        web3,
        exchange_abi,
        token_abi,
        exchange_address,
        address_oracle)


def test_validate(order_trustlines, exchange_proxy):
    assert exchange_proxy.validate(order_trustlines)


def test_not_enough_funds(order_token, exchange_proxy):
    assert not exchange_proxy.validate_funds(order_token)
    assert not exchange_proxy.validate(order_token)


def test_enough_funds(order_token, exchange_proxy, testnetworks):
    unw_eth_contract = testnetworks[2]
    unw_eth_contract.functions.deposit().transact({'from': order_token.maker_address, 'value': 100})

    assert exchange_proxy.validate_funds(order_token)
    assert exchange_proxy.validate(order_token)


def test_no_filled_amount(order_token, exchange_proxy):
    assert exchange_proxy.get_filled_amount(order_token) == 0


def test_filled_amount(order_trustlines, exchange_proxy, testnetworks, maker, taker):
    order = order_trustlines

    exchange_contract = testnetworks[1]
    exchange_contract.functions.fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100,
        [],
        [maker],
        order.v,
        order.r,
        order.s).transact({'from': taker})

    assert exchange_proxy.get_filled_amount(order) == 100
    assert exchange_proxy.validate_filled_amount(order)

    exchange_contract.functions.fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100,
        [],
        [maker],
        order.v,
        order.r,
        order.s).transact({'from': taker})

    assert exchange_proxy.get_filled_amount(order) == 200
    assert not exchange_proxy.validate_filled_amount(order)


def test_cancelled_amount(order_trustlines, exchange_proxy, testnetworks, maker, taker):
    order = order_trustlines

    exchange_contract = testnetworks[1]
    exchange_contract.functions.cancelOrder(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100).transact({'from': maker})

    assert exchange_proxy.get_cancelled_amount(order) == 100


def test_unavailable_amount(order_trustlines, exchange_proxy, testnetworks, maker, taker):
    order = order_trustlines

    exchange_contract = testnetworks[1]

    exchange_contract.functions.fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        10,
        [],
        [maker],
        order.v,
        order.r,
        order.s).transact({'from': taker})

    exchange_contract.functions.cancelOrder(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        10).transact({'from': maker})

    assert exchange_proxy.get_unavailable_amount(order) == 20


def test_listen_on_fill(order_trustlines, exchange_proxy, testnetworks, maker, taker):
    logs = []

    def log(order_hash, maker_token_amount, taker_token_amount):
        logs.append((order_hash, maker_token_amount, taker_token_amount))

    order = order_trustlines

    exchange_proxy.start_listen_on_fill(log)
    gevent.sleep(0.001)

    exchange_contract = testnetworks[1]
    exchange_contract.functions.fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100,
        [taker],
        [],
        order.v,
        order.r,
        order.s).transact({'from': taker})

    gevent.sleep(1)

    log1 = logs[0]
    assert log1[0] == order.hash()
    assert log1[1] == 50
    assert log1[2] == 100


def test_listen_on_cancel(order_token, exchange_proxy, testnetworks, maker, taker):
    logs = []

    def log(order_hash, maker_token_amount, taker_token_amount):
        logs.append((order_hash, maker_token_amount, taker_token_amount))

    order = order_token

    exchange_proxy.start_listen_on_cancel(log)
    gevent.sleep(0.001)

    exchange_contract = testnetworks[1]
    exchange_contract.functions.cancelOrder(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100).transact({'from': maker})

    gevent.sleep(1)

    log1 = logs[0]
    assert log1[0] == order.hash()
    assert log1[1] == 50
    assert log1[2] == 100
