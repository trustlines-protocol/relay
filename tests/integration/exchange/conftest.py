import pytest
from sqlalchemy import create_engine

from relay.exchange.order import SignableOrder
from relay.constants import NULL_ADDRESS


@pytest.fixture()
def engine():
    return create_engine('sqlite:///:memory:')


@pytest.fixture()
def orders(addresses, test_account):
    A, B, C, D = addresses
    maker = test_account.address
    orders = [
        SignableOrder(
            exchange_address=A,
            maker_address=maker,
            taker_address=NULL_ADDRESS,
            maker_token=C,
            taker_token=D,
            fee_recipient=NULL_ADDRESS,
            maker_token_amount=100,
            taker_token_amount=200,
            maker_fee=0,
            taker_fee=0,
            expiration_timestamp_in_sec=1230000000000,
            salt=123
        ), SignableOrder(
            exchange_address=A,
            maker_address=maker,
            taker_address=NULL_ADDRESS,
            maker_token=C,
            taker_token=D,
            fee_recipient=NULL_ADDRESS,
            maker_token_amount=100,
            taker_token_amount=200,
            maker_fee=0,
            taker_fee=0,
            expiration_timestamp_in_sec=1234000000000,
            salt=123
        ), SignableOrder(
            exchange_address=A,
            maker_address=maker,
            taker_address=NULL_ADDRESS,
            maker_token=B,
            taker_token=D,
            fee_recipient=NULL_ADDRESS,
            maker_token_amount=100,
            taker_token_amount=200,
            maker_fee=0,
            taker_fee=0,
            expiration_timestamp_in_sec=1230000000000,
            salt=123
        ), SignableOrder(
            exchange_address=A,
            maker_address=maker,
            taker_address=NULL_ADDRESS,
            maker_token=D,
            taker_token=C,
            fee_recipient=NULL_ADDRESS,
            maker_token_amount=100,
            taker_token_amount=200,
            maker_fee=0,
            taker_fee=0,
            expiration_timestamp_in_sec=1230000000000,
            salt=123
        ), SignableOrder(
            exchange_address=A,
            maker_address=maker,
            taker_address=NULL_ADDRESS,
            maker_token=C,
            taker_token=D,
            fee_recipient=NULL_ADDRESS,
            maker_token_amount=100,
            taker_token_amount=100,
            maker_fee=0,
            taker_fee=0,
            expiration_timestamp_in_sec=1234000000000,
            salt=123
        )]
    for order in orders:
        order.sign(test_account.private_key)
    return orders


@pytest.fixture()
def order(orders):
    return orders[0]
