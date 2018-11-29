#! /usr/bin/env pytest
"""test the cost accumulators, SenderPaysCostAccumulatorSnapshot and ReceiverPaysCostAccumulatorSnapshot
"""
import pytest

from relay.network_graph import graph
import networkx as nx
from relay.network_graph.trustline_data import set_balance, set_creditline


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


@pytest.fixture
def simplegraph():
    graph = nx.graph.Graph()

    for i in range(1, 10):
        edge_data = zero_edge_data()
        set_creditline(edge_data, i, i + 1, 1000)  # creditline given from i to i+1
        set_creditline(edge_data, i + 1, i, 1000)  # creditline given from i+1 to i
        graph.add_edge(i, i + 1, **edge_data)
    return graph


@pytest.fixture(
    params=[
        graph.SenderPaysCostAccumulatorSnapshot,
        graph.ReceiverPaysCostAccumulatorSnapshot,
    ]
)
def cost_accumulator_class(request):
    return request.param


def test_cost_accumulator_max_hops(cost_accumulator_class, simplegraph):
    acc = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=150, capacity_imbalance_fee_divisor=100, max_hops=8
    )

    fee, num_hops = acc.compute_cost_for_path(simplegraph, list(range(1, 10)))
    assert num_hops == 8
    assert fee >= 8


def test_cost_accumulator_max_hops_exceeded(cost_accumulator_class, simplegraph):
    acc = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=150, capacity_imbalance_fee_divisor=100, max_hops=7
    )

    with pytest.raises(nx.NetworkXNoPath):
        acc.compute_cost_for_path(simplegraph, list(range(1, 10)))


def test_max_fees(cost_accumulator_class, simplegraph):
    acc = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000, value=150, capacity_imbalance_fee_divisor=100
    )
    fee, num_hops = acc.compute_cost_for_path(simplegraph, list(range(1, 10)))

    acc2 = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000,
        value=150,
        capacity_imbalance_fee_divisor=100,
        max_fees=fee,
    )

    assert fee, num_hops == acc2.compute_cost_for_path(simplegraph, list(range(1, 10)))

    acc3 = graph.SenderPaysCostAccumulatorSnapshot(
        timestamp=1500000000,
        value=150,
        capacity_imbalance_fee_divisor=100,
        max_fees=fee - 1,
    )

    with pytest.raises(nx.NetworkXNoPath):
        acc3.compute_cost_for_path(simplegraph, list(range(1, 10)))


@pytest.fixture
def capgraph():
    capgraph = nx.graph.Graph()
    edge_data = zero_edge_data()
    set_balance(edge_data, 1, 2, 500)
    set_creditline(edge_data, 2, 1, 1000)  # creditline given from 2 to 1 is 1000
    capgraph.add_edge(1, 2, **edge_data)
    return capgraph


@pytest.mark.parametrize("value", [0, 100, 500, 750, 1000, 1100, 1500])
def test_capacity(cost_accumulator_class, value, capgraph):
    """test that the cost accumulator take the balance and the right creditline
    given into account"""

    if cost_accumulator_class == graph.SenderPaysCostAccumulatorSnapshot:
        path = [2, 1]  # need to reverse the path for SenderPaysCostAccumulatorSnapshot
    else:
        path = [1, 2]

    acc = cost_accumulator_class(
        timestamp=1500000000, value=value, capacity_imbalance_fee_divisor=0
    )
    assert acc.compute_cost_for_path(capgraph, path) == (0, 1)


def test_capacity_exceeded(cost_accumulator_class, capgraph):
    """test that the cost accumulator doesn't exceed the creditline, it should
    throw an error instead"""
    if cost_accumulator_class == graph.SenderPaysCostAccumulatorSnapshot:
        path = [2, 1]  # need to reverse the path for SenderPaysCostAccumulatorSnapshot
    else:
        path = [1, 2]

    with pytest.raises(nx.NetworkXNoPath):
        acc = cost_accumulator_class(
            timestamp=1500000000, value=1501, capacity_imbalance_fee_divisor=0
        )
        acc.compute_cost_for_path(capgraph, path)
