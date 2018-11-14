import pytest

from relay.network_graph.trustline_data import (
    set,
    get,
    set_balance,
    get_balance,
    set_creditline,
    get_creditline,
    set_interest_rate,
    get_interest_rate, set_fees_outstanding, get_fees_outstanding, set_mtime, get_mtime)

a = "0xA"
b = "0xB"
key = "test"


@pytest.fixture()
def data():
    return {}


def test_set_get(data):
    set(data, a, b, {key: 1}, {key: -1})
    assert get(a, b, data[key], -data[key]) == 1
    assert get(b, a, data[key], -data[key]) == -1


def test_balance(data):
    set_balance(data, a, b, 100)
    assert get_balance(data, a, b) == 100
    assert get_balance(data, b, a) == -100


def test_creditline(data):
    set_creditline(data, a, b, 100)
    set_creditline(data, b, a, 200)
    assert get_creditline(data, a, b) == 100
    assert get_creditline(data, b, a) == 200


def test_interests(data):
    set_interest_rate(data, a, b, 100)
    set_interest_rate(data, b, a, 200)
    assert get_interest_rate(data, a, b) == 100
    assert get_interest_rate(data, b, a) == 200


def test_fees_outstanding(data):
    set_fees_outstanding(data, a, b, 100)
    set_fees_outstanding(data, b, a, 200)
    assert get_fees_outstanding(data, a, b) == 100
    assert get_fees_outstanding(data, b, a) == 200


def test_mtime(data):
    set_mtime(data, 12345)
    assert get_mtime(data) == 12345
