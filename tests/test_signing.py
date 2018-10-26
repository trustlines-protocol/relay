import pytest
from relay.signing import eth_validate, eth_sign

pytestmark = pytest.mark.unit


def test_eth_validate(test_account):
    msg_hash = bytes(32)
    vrs = eth_sign(msg_hash, test_account.private_key)
    assert eth_validate(msg_hash, vrs, test_account.address)


def test_eth_validate_fail(test_account):
    msg_hash1 = bytes(32)
    msg_hash2 = (123).to_bytes(32, byteorder='big')
    vrs = eth_sign(msg_hash1, test_account.private_key)
    assert not eth_validate(msg_hash2, vrs, test_account.address)


def test_eth_validate_fail2(test_account):
    msg_hash = bytes(32)
    v = 27
    r = 18
    s = 2748
    assert not eth_validate(msg_hash, (v, r, s), test_account.address)
