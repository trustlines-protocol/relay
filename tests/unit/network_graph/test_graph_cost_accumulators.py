#! /usr/bin/env pytest
"""test the cost accumulators, SenderPaysCostAccumulatorSnapshot and ReceiverPaysCostAccumulatorSnapshot
"""
from typing import List

import attr
import networkx as nx
import pytest

from relay.network_graph import alg, graph
from relay.network_graph.trustline_data import set_balance, set_creditline


def zero_edge_data():
    return dict(
        creditline_ab=0,
        creditline_ba=0,
        interest_ab=0,
        interest_ba=0,
        m_time=0,
        balance_ab=0,
        is_frozen=False,
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
    assert acc.compute_cost_for_path(capgraph, path)[0] == 0


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


# -- the rest of this file tests with the Transfer testdata


def build_graph(*, addresses: List, creditlines: List, balances: List):
    """build a simple graph with zero balances and creditlines between each
    consecutive pairs in addresses.
    creditlines[i] is set as the creditline given from addresses[i+1] to
    addresses[i].
    I.e. this is setup in a way that a payment from addresses[0] to
    addresses[-1] could work, given that sufficient creditlines are available
    at each step.
    """
    assert len(creditlines) == len(addresses) - 1
    gr = nx.graph.Graph()
    for a, b, creditline, balance in zip(
        addresses, addresses[1:], creditlines, balances
    ):
        edge = zero_edge_data()
        set_creditline(edge, b, a, creditline)  # creditline given by b to a
        set_balance(edge, a, b, balance)
        gr.add_edge(a, b, **edge)
    return gr


@attr.s(auto_attribs=True)
class TransferInfo:
    addresses: List
    path: List
    capacity_imbalance_fee_divisor: int
    fees_paid_by: str
    value: int
    timestamp: int
    balances_before_transfer: List
    balances_after_transfer: List
    expected_fees: int
    cost_accumulator: alg.CostAccumulator
    minimal_creditlines: List

    def assert_expected_cost(self, gr):
        """try to compute the costs for the transfer and fail if they don't match with the expected value"""
        result = self.cost_accumulator.compute_cost_for_path(gr, self.path)
        print("COST:", result)
        assert result[0] == self.expected_fees

    def assert_find_path(self, gr):
        """ensure that least_cost_path is able to find a path and that the cost
        is as expected"""
        cost, path_found = alg.least_cost_path(
            graph=gr,
            starting_nodes={self.path[0]},
            target_nodes={self.path[-1]},
            cost_accumulator=self.cost_accumulator,
        )
        assert cost[0] == self.expected_fees
        assert path_found == self.path

    def insufficient_creditlines(self):
        """yield creditlines that are insufficent for a transfer of the given
        value"""
        num_hops = len(self.addresses) - 1
        for i in range(num_hops):
            creditlines = [100000000] * num_hops
            creditlines[i] = self.minimal_creditlines[i] - 1
            yield creditlines


@pytest.fixture
def transfer_info(Transfer):
    """build a TransferInfo object for the given Transfer testdata"""
    addresses = Transfer["input_data"]["addresses"]
    capacity_imbalance_fee_divisor = Transfer["input_data"][
        "capacity_imbalance_fee_divisor"
    ]
    fees_paid_by = Transfer["input_data"]["fees_paid_by"]
    value = Transfer["input_data"]["value"]
    balances_before_transfer = Transfer["input_data"]["balances_before"]

    balances_after_transfer = Transfer["balances_after"]

    timestamp = 1500000000
    if fees_paid_by == "sender":
        cost_accumulator = graph.SenderPaysCostAccumulatorSnapshot(
            timestamp=timestamp,
            value=value,
            capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
        )
        path = list(reversed(addresses))
        #      balance_after_transfer[0] == balances_before_transfer[0] - value - fees
        # =>   fees == balances_before_transfer[0] - value - balances_after_transfer[0]
        expected_fees = balances_before_transfer[0] - value - balances_after_transfer[0]
    else:
        cost_accumulator = graph.ReceiverPaysCostAccumulatorSnapshot(
            timestamp=timestamp,
            value=value,
            capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
        )
        path = addresses
        # expected_fees = receivers_balance_before + value - receivers_balance_after
        # ==> expected_fees = - balances_before_transfer[-1] + value - (- balances_after_transfer[-1])
        # ==> expected_fees = balances_after_transfer[-1] - balances_before_transfer[-1] + value
        expected_fees = (
            balances_after_transfer[-1] - balances_before_transfer[-1] + value
        )

    return TransferInfo(
        addresses=addresses,
        balances_after_transfer=balances_after_transfer,
        capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
        fees_paid_by=fees_paid_by,
        value=value,
        timestamp=1500000000,
        path=path,
        expected_fees=expected_fees,
        cost_accumulator=cost_accumulator,
        minimal_creditlines=[-b for b in balances_after_transfer],
        balances_before_transfer=balances_before_transfer,
    )


def test_transfer_ample_creditlines(transfer_info: TransferInfo):
    """test that the transfer succeeds with ample room for the creditlines"""
    print(transfer_info)
    gr = build_graph(
        addresses=transfer_info.addresses,
        creditlines=[100000000] * (len(transfer_info.addresses) - 1),
        balances=transfer_info.balances_before_transfer,
    )
    transfer_info.assert_expected_cost(gr)
    transfer_info.assert_find_path(gr)


def test_transfer_minimal_creditlines(transfer_info: TransferInfo):
    """test that the transfer succeeds with the minimal creditlines required"""
    print(transfer_info)
    gr = build_graph(
        addresses=transfer_info.addresses,
        creditlines=transfer_info.minimal_creditlines,
        balances=transfer_info.balances_before_transfer,
    )
    transfer_info.assert_expected_cost(gr)
    transfer_info.assert_find_path(gr)


def test_transfer_creditlines_insufficient(transfer_info: TransferInfo):
    """test that the transfer fails if one of the creditlines is too small"""
    print(transfer_info)
    for creditlines in transfer_info.insufficient_creditlines():
        gr = build_graph(
            addresses=transfer_info.addresses,
            creditlines=creditlines,
            balances=transfer_info.balances_before_transfer,
        )
        with pytest.raises(nx.NetworkXNoPath):
            transfer_info.assert_expected_cost(gr)


def test_find_path_creditlines_insufficient(transfer_info: TransferInfo):
    """test that the transfer fails if one of the creditlines is too small"""
    print(transfer_info)
    for creditlines in transfer_info.insufficient_creditlines():
        gr = build_graph(
            addresses=transfer_info.addresses,
            creditlines=creditlines,
            balances=transfer_info.balances_before_transfer,
        )
        with pytest.raises(nx.NetworkXNoPath):
            transfer_info.assert_find_path(gr)
