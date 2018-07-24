import pytest


from relay.exchange.order import Order
from relay.api.exchange.schemas import OrderSchema


@pytest.fixture()
def order():
    return Order('0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9', '0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9',
                 '0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9', '0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9',
                 '0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9', '0x55bdaAf9f941A5BB3EacC8D876eeFf90b90ddac9', 100, 100,
                 100, 100, 10000, 1000, 28, bytes([12]), bytes([20]))


def test_sig_v(order):
    serialized_order = OrderSchema().dump(order).data
    assert type(serialized_order['ecSignature']['v']) == int


def test_sig_rs(order):
    serialized_order = OrderSchema().dump(order).data
    r = serialized_order['ecSignature']['r']
    s = serialized_order['ecSignature']['s']
    for x in r, s:
        assert type(s) == str
        assert x[0:2] == '0x'
        assert len(x) == 66


def test_sig_lowercase(order):
    serialized_order = OrderSchema().dump(order).data
    r = serialized_order['ecSignature']['r']
    s = serialized_order['ecSignature']['s']
    for x in r, s:
        assert x.islower()
