from relay.network_graph.fees import (
    calculate_fees,
    calculate_fees_reverse,
    imbalance_generated,
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
