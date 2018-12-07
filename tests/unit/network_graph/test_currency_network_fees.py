#! pytest

import pytest

import networkx as nx
from relay.network_graph.trustline_data import set_creditline
from relay.network_graph import graph


def zero_edge_data():
    return dict(
        creditline_ab=0,
        creditline_ba=0,
        interest_ab=0,
        interest_ba=0,
        fees_outstanding_a=0,
        fees_outstanding_b=0,
        m_time=0,
        balance_ab=0,
    )


trustlines = [
    (0, 1, 100, 150),
    (1, 2, 200, 250),
    (2, 3, 300, 350),
    (3, 4, 400, 450),
    (0, 4, 500, 550),
]  # (A, B, clAB, clBA)


@pytest.fixture()
def currency_network_with_trustlines():
    graph = nx.graph.Graph()
    for a, b, creditline_ab, creditline_ba in trustlines:
        edge_data = zero_edge_data()
        set_creditline(edge_data, a, b, creditline_ab)
        set_creditline(edge_data, b, a, creditline_ba)
        graph.add_edge(a, b, **edge_data)
    return graph


@pytest.fixture(
    params=[
        graph.SenderPaysCostAccumulatorSnapshot,
        graph.ReceiverPaysCostAccumulatorSnapshot,
    ]
)
def cost_accumulator_class(request):
    return request.param


@pytest.mark.parametrize("value", [0, 10, 100, 145, 146, 147, 148, 149, 150])
def test_transfer_0_mediators(
    currency_network_with_trustlines, cost_accumulator_class, value
):
    """fees must be zero, when having no mediators"""
    cost_accumulator = cost_accumulator_class(
        timestamp=1500000000,
        value=value,
        capacity_imbalance_fee_divisor=100,
        max_fees=0,
    )
    path = [0, 1]
    if cost_accumulator_class == graph.SenderPaysCostAccumulatorSnapshot:
        path.reverse()

    assert (0, 1) == cost_accumulator.compute_cost_for_path(
        currency_network_with_trustlines, path
    )


def test_transfer_0_mediators_not_enough_credit(
    currency_network_with_trustlines, cost_accumulator_class
):
    """fees must be zero, when having no mediators"""
    cost_accumulator = cost_accumulator_class(
        timestamp=1500000000, value=151, capacity_imbalance_fee_divisor=100, max_fees=0
    )
    path = [0, 1]
    if cost_accumulator_class == graph.SenderPaysCostAccumulatorSnapshot:
        path.reverse()
    with pytest.raises(nx.NetworkXNoPath):
        cost_accumulator.compute_cost_for_path(currency_network_with_trustlines, path)


def test_transfer_1_mediators(currency_network_with_trustlines):
    cost_accumulator = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=50, capacity_imbalance_fee_divisor=100, max_fees=1
    )
    assert cost_accumulator.compute_cost_for_path(
        currency_network_with_trustlines, [2, 1, 0]
    ) == (1, 2)


def test_transfer_1_mediators_not_enough_credit(currency_network_with_trustlines):
    cost_accumulator = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000,
        value=151 - 2,
        capacity_imbalance_fee_divisor=100,
        max_fees=2,
    )
    with pytest.raises(nx.NetworkXNoPath):
        cost_accumulator.compute_cost_for_path(
            currency_network_with_trustlines, [2, 1, 0]
        )


def test_transfer_3_mediators(currency_network_with_trustlines):
    cost_accumulator = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=100, capacity_imbalance_fee_divisor=100, max_fees=6
    )
    assert cost_accumulator.compute_cost_for_path(
        currency_network_with_trustlines, [4, 3, 2, 1, 0]
    ) == (6, 4)


def test_rounding_fee(currency_network_with_trustlines):
    cost_accumulator = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=99, capacity_imbalance_fee_divisor=100, max_fees=1
    )
    assert cost_accumulator.compute_cost_for_path(
        currency_network_with_trustlines, [2, 1, 0]
    ) == (1, 2)


def test_max_fee(currency_network_with_trustlines):
    cost_accumulator = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=110, capacity_imbalance_fee_divisor=100, max_fees=1
    )
    with pytest.raises(nx.NetworkXNoPath):
        cost_accumulator.compute_cost_for_path(
            currency_network_with_trustlines, [2, 1, 0]
        )
