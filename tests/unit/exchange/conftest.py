import pytest
from ethereum import tester
from eth_utils import to_checksum_address

from relay.exchange.order import Order, SignableOrder
from relay.constants import NULL_ADDRESS


@pytest.fixture()
def invalid_signature_order(addresses):
    A, B, C, D = addresses
    return Order(
        exchange_address=A,
        maker_address=B,
        taker_address=NULL_ADDRESS,
        maker_token=C,
        taker_token=D,
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=123,
        salt=123,
        v=27,
        r=(123).to_bytes(32, byteorder='big'),
        s=(345).to_bytes(32, byteorder='big'))


@pytest.fixture()
def invalid_exchange_order(addresses):
    A, B, C, D = addresses
    maker = tester.a0
    order = SignableOrder(
        exchange_address='0x379162d7682cb8bb6435c47E0b8b562eafe66971',
        maker_address=to_checksum_address(maker),
        taker_address=NULL_ADDRESS,
        maker_token=C,
        taker_token=D,
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=123,
        salt=123)
    order.sign(tester.k0)
    return order


@pytest.fixture()
def invalid_taker_order(addresses):
    A, B, C, D = addresses
    maker = tester.a0
    order = SignableOrder(
        exchange_address=A,
        maker_address=to_checksum_address(maker),
        taker_address=B,
        maker_token=C,
        taker_token=D,
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=123,
        salt=123)
    order.sign(tester.k0)
    return order


@pytest.fixture()
def expired_order(addresses):
    A, B, C, D = addresses
    maker = tester.a0
    order = SignableOrder(
        exchange_address=A,
        maker_address=to_checksum_address(maker),
        taker_address=C,
        maker_token=C,
        taker_token=D,
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=123,
        salt=123)
    order.sign(tester.k0)
    return order


@pytest.fixture()
def valid_order(addresses):
    A, B, C, D = addresses
    maker = tester.a0
    order = SignableOrder(
        exchange_address=A,
        maker_address=to_checksum_address(maker),
        taker_address=NULL_ADDRESS,
        maker_token=C,
        taker_token=D,
        fee_recipient=NULL_ADDRESS,
        maker_token_amount=100,
        taker_token_amount=200,
        maker_fee=0,
        taker_fee=0,
        expiration_timestamp_in_sec=1517161470000,
        salt=123)
    order.sign(tester.k0)

    return order
