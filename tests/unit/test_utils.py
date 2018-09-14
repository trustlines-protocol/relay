from relay.utils import sha3


def test_sha3():
    assert sha3('foobar') == '0x38d18acb67d25c8bb9942764b62f18e17054f66a817bd4295423adf9ed98873e'
