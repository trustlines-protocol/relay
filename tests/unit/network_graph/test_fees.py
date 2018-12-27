from relay.network_graph.fees import (
    calculate_fees,
    calculate_fees_reverse,
    imbalance_generated,
    estimate_fee_from_imbalance
)


def test_imbalance_generated(ImbalanceGenerated):
    balance = ImbalanceGenerated["input_data"]["balance"]
    value = ImbalanceGenerated["input_data"]["value"]
    expected_imbalance_generated = ImbalanceGenerated["imbalance_generated"]
    assert (
        imbalance_generated(balance=balance, value=value)
        == expected_imbalance_generated
    )


def test_calculate_fees(CalculateFee):
    capacity_imbalance_fee_divisor = CalculateFee["input_data"][
        "capacity_imbalance_fee_divisor"
    ]
    imbalance_generated = CalculateFee["input_data"]["imbalance_generated"]
    expected_fees = CalculateFee["fees"]
    assert (
        calculate_fees(imbalance_generated, capacity_imbalance_fee_divisor)
        == expected_fees
    )


def test_calculate_fees_reverse(CalculateFee):
    capacity_imbalance_fee_divisor = CalculateFee["input_data"][
        "capacity_imbalance_fee_divisor"
    ]
    imbalance_generated = CalculateFee["input_data"]["imbalance_generated"]
    expected_fees_reverse = CalculateFee["fees_reverse"]
    assert (
        calculate_fees_reverse(imbalance_generated, capacity_imbalance_fee_divisor)
        == expected_fees_reverse
    )


def test_estimate_fees_from_capacity_single_hop():
    """
    Tests the estimation for a single hop
    The estimation has to be an upper bound so the actual fees have to be lower
    """
    fees = estimate_fee_from_imbalance(100, 12345)
    assert fees == 123


def test_estimate_fees_from_capacity_single_hop_upper_edge_case():
    """Tests the upper value of the edge case for the estimation"""
    fees = estimate_fee_from_imbalance(100, 101)
    assert fees == 1


def test_estimate_fees_from_capacity_single_hop_lower_edge_case():
    """Tests the lower value of the edge case for the estimation"""
    fees = estimate_fee_from_imbalance(100, 100)
    assert fees == 1


def test_estimate_fees_from_capacity_single_hop_sanity():
    """Tests whether for small values outside of indeterminate case, the estimation is exact"""
    fees = estimate_fee_from_imbalance(100, 150)
    assert fees == 2

