from relay.network_graph.fees import imbalance_fee, new_balance, estimate_fees_from_capacity


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


def test_estimate_fees_from_capacity_single_hop():
    """
    Tests the estimation for a single hop
    The estimation has to be an upper bound so the actual fees have to be lower
    """
    fees = estimate_fees_from_capacity(100, 12345, [12345])
    assert fees == 123


def test_estimate_fees_from_capacity_single_hop_upper_edge_case():
    """Tests the upper value of the edge case for the estimation"""
    fees = estimate_fees_from_capacity(100, 101, [101])
    assert fees == 1


def test_estimate_fees_from_capacity_single_hop_lower_edge_case():
    """Tests the lower value of the edge case for the estimation"""
    fees = estimate_fees_from_capacity(100, 100, [100])
    assert fees == 1


def test_estimate_fees_from_capacity_single_hop_sanity():
    """Tests whether for small values outside of indeterminate case, the estimation is exact"""
    fees = estimate_fees_from_capacity(100, 150, [150])
    assert fees == 2


def test_estimate_fees_from_capacity_last_hop_smallest():
    fees = estimate_fees_from_capacity(100, 104, [500, 104])
    assert fees >= 4


def test_estimate_fees_from_capacity_first_hop_smallest():
    fees = estimate_fees_from_capacity(100, 104, [104, 500])
    assert fees >= 4


def test_estimate_fees_from_capacity_three_hops():
    fees = estimate_fees_from_capacity(100, 106, [112, 106, 250])
    assert fees >= 6


def test_estimate_fees_from_capacity_eight_hops():
    fees = estimate_fees_from_capacity(100, 116, [116, 116, 116, 116, 116, 116, 116, 116])
    assert fees >= 16
