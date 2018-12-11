from relay.network_graph.fees import (estimate_fees_from_capacity,
                                      calculate_fees, calculate_fees_reverse, imbalance_generated)


def test_imbalance_generated(ImbalanceGenerated):
    balance = ImbalanceGenerated["input_data"]["balance"]
    value = ImbalanceGenerated["input_data"]["value"]
    expected = ImbalanceGenerated["imbalance_generated"]
    assert imbalance_generated(balance=balance, value=value) == expected


def test_calculate_fees(CalculateFeeGenerator):
    capacity_imbalance_fee_divisor = CalculateFeeGenerator["input_data"][
        "capacity_imbalance_fee_divisor"
    ]
    imbalance_generated = CalculateFeeGenerator["input_data"]["imbalance_generated"]
    calculateFees = CalculateFeeGenerator["calculateFees"]
    assert (
        calculate_fees(imbalance_generated, capacity_imbalance_fee_divisor)
        == calculateFees
    )


def test_calculate_fees_reverse(CalculateFeeGenerator):
    capacity_imbalance_fee_divisor = CalculateFeeGenerator["input_data"][
        "capacity_imbalance_fee_divisor"
    ]
    imbalance_generated = CalculateFeeGenerator["input_data"]["imbalance_generated"]
    calculateFeesReverse = CalculateFeeGenerator["calculateFeesReverse"]
    assert (
        calculate_fees_reverse(imbalance_generated, capacity_imbalance_fee_divisor)
        == calculateFeesReverse
    )


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
