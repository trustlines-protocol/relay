from relay.network_graph.fees import imbalance_fee, new_balance


def test_increase_imbalance_fee():
    assert imbalance_fee(100, 0, 500) == 6


def test_decrease_imbalance_fee():
    assert imbalance_fee(100, 500, 500) == 0


def test_both_imbalance_fee():
    assert imbalance_fee(50, 250, 500) == 6


def test_from_negative_imbalance_fee():
    assert imbalance_fee(50, -250, 250) == 6


def test_add_more_imbalance_fee():
    assert imbalance_fee(100, -250, 500) == 6


def test_too_small_imbalance_fee():
    assert imbalance_fee(100, 0, 50) == 1


def test_new_balance_increase():
    assert new_balance(20, 0, 500) == -526


def test_new_balance_decrease():
    assert new_balance(20, 500, 500) == 0


def test_new_balance_both():
    assert new_balance(20, 250, 500) == -263


def test_new_balance_from_negative():
    assert new_balance(50, -250, 250) == -506
