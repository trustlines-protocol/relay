import gevent
import pytest
from eth_utils import to_checksum_address
from ethereum import tester

from relay.blockchain.exchange_proxy import ExchangeProxy
from relay.constants import NULL_ADDRESS
from relay.exchange.order import SignableOrder


@pytest.fixture()
def order_token(exchange_address, network_addresses_with_exchange, unw_eth_address):
    maker = to_checksum_address(tester.a0)
    order = SignableOrder(
        exchange_address=exchange_address,
        maker_address=maker,
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
    order.sign(tester.k0)
    return order


@pytest.fixture()
def order_trustlines(exchange_address, network_addresses_with_exchange, unw_eth_address):
    maker = to_checksum_address(tester.a0)
    order = SignableOrder(
        exchange_address=exchange_address,
        maker_address=maker,
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
    order.sign(tester.k0)
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
    unw_eth_contract.transact({'from': order_token.maker_address, 'value': 100}).deposit()

    assert exchange_proxy.validate_funds(order_token)
    assert exchange_proxy.validate(order_token)


def test_no_filled_amount(order_token, exchange_proxy):
    assert exchange_proxy.get_filled_amount(order_token) == 0


def test_filled_amount(order_trustlines, exchange_proxy, testnetworks, accounts):
    order = order_trustlines
    maker, taker, *rest = accounts

    exchange_contract = testnetworks[1]
    exchange_contract.transact({'from': taker}).fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100,
        [],
        [maker],
        order.v,
        order.r,
        order.s)

    assert exchange_proxy.get_filled_amount(order) == 100
    assert exchange_proxy.validate_filled_amount(order)

    exchange_contract.transact({'from': taker}).fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100,
        [],
        [maker],
        order.v,
        order.r,
        order.s)

    assert exchange_proxy.get_filled_amount(order) == 200
    assert not exchange_proxy.validate_filled_amount(order)


def test_listen_on_fill(order_trustlines, exchange_proxy, testnetworks, accounts):
    logs = []

    def log(order_hash, maker_token_amount, taker_token_amount):
        logs.append((order_hash, maker_token_amount, taker_token_amount))

    order = order_trustlines
    maker, taker, *rest = accounts

    exchange_proxy.start_listen_on_fill(log)
    gevent.sleep(0.001)

    exchange_contract = testnetworks[1]
    exchange_contract.transact({'from': taker}).fillOrderTrustlines(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100,
        [taker],
        [],
        order.v,
        order.r,
        order.s)

    gevent.sleep(1)

    log1 = logs[0]
    assert log1[0].encode('Latin-1') == order.hash()  # encoding because of bug in web3
    assert log1[1] == 50
    assert log1[2] == 100


def test_listen_on_cancel(order_token, exchange_proxy, testnetworks, accounts):
    logs = []

    def log(order_hash, maker_token_amount, taker_token_amount):
        logs.append((order_hash, maker_token_amount, taker_token_amount))

    order = order_token
    maker, taker, *rest = accounts

    exchange_proxy.start_listen_on_cancel(log)
    gevent.sleep(0.001)

    exchange_contract = testnetworks[1]
    exchange_contract.transact({'from': maker}).cancelOrder(
        [order.maker_address, order.taker_address, order.maker_token, order.taker_token, order.fee_recipient],
        [order.maker_token_amount, order.taker_token_amount, order.maker_fee,
         order.taker_fee, order.expiration_timestamp_in_sec, order.salt],
        100)

    gevent.sleep(1)

    log1 = logs[0]
    assert log1[0].encode('Latin-1') == order.hash()  # encoding because of bug in web3
    assert log1[1] == 50
    assert log1[2] == 100
