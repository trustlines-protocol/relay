from relay.exchange.order import Order


def test_invalid_signature(invalid_signature_order: Order):
    assert not invalid_signature_order.validate_signature()
    assert not invalid_signature_order.validate()


def test_invalid_address(invalid_exchange_order: Order):
    assert not invalid_exchange_order.validate_addresses()
    assert not invalid_exchange_order.validate()


def test_valid_order(valid_order: Order):
    assert valid_order.validate_addresses()
    assert valid_order.validate_signature()
    assert valid_order.validate()


def test_expired(valid_order: Order):
    assert not valid_order.is_expired(0)
    assert valid_order.is_expired(1517161471000)
