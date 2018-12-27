from relay.network_graph.fees import (
    calculate_fees,
    calculate_fees_reverse,
    imbalance_generated,
    estimate_max_fee_from_max_imbalance,
    estimate_sendable_from_one_limiting_capacity
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
    imbalance = 12345
    fee_estimation = estimate_max_fee_from_max_imbalance(100, imbalance)
    fee_actual = calculate_fees(imbalance - fee_estimation, 100)
    assert fee_estimation >= fee_actual


def test_estimate_max_fees_from_capacity_single_hop_upper_edge_case():
    """Tests the upper value of the edge case for the estimation"""
    imbalance = 101
    fee_estimation = estimate_max_fee_from_max_imbalance(100, imbalance)
    fee_actual = calculate_fees(imbalance - fee_estimation, 100)
    assert fee_estimation >= fee_actual


def test_estimate_max_fees_from_capacity_single_hop_lower_edge_case():
    """Tests the lower value of the edge case for the estimation"""
    imbalance = 100
    fee_estimation = estimate_max_fee_from_max_imbalance(100, imbalance)
    fee_actual = calculate_fees(imbalance - fee_estimation, 100)
    assert fee_estimation >= fee_actual


def test_estimate_max_fees_from_capacity_single_hop_smaller_than_divisor():
    """Tests the fee estimation with a value smaller than the divisor"""
    imbalance = 42
    fee_estimation = estimate_max_fee_from_max_imbalance(100, imbalance)
    fee_actual = calculate_fees(imbalance - fee_estimation, 100)
    assert fee_estimation >= fee_actual


def test_estimate_max_fees_from_capacity_single_hop_sanity():
    """Tests whether for small values outside of indeterminate case, the estimation is exact"""
    imbalance = 150
    fee_estimation = estimate_max_fee_from_max_imbalance(100, imbalance)
    fee_actual = calculate_fees(imbalance - fee_estimation, 100)
    assert fee_estimation >= fee_actual


def test_estimate_max_fees_from_capacity_single_hop_high_value():
    """Tests whether for small values outside of indeterminate case, the estimation is exact"""
    imbalance = 123456789
    fee_estimation = estimate_max_fee_from_max_imbalance(100, imbalance)
    fee_actual = calculate_fees(imbalance - fee_estimation, 100)
    assert fee_estimation >= fee_actual

