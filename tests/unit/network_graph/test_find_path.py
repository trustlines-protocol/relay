import networkx as nx
import pytest

from relay.network_graph import alg


class FeeCostAccumulator(alg.CostAccumulator):
    def zero(self):
        return 0

    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node, node, dst, graph_data
    ):
        return cost_from_start_to_node + graph_data["fee"]


@pytest.fixture()
def graph():
    g = nx.Graph()

    # 1 -> 2 -> 3
    # 1 -> 3

    g.add_edge(1, 2, fee=1)
    g.add_edge(2, 3, fee=1)
    g.add_edge(1, 3, fee=100)
    return g


def sanity_check_fees(graph, cost_path):
    print(f"Checking {cost_path}")
    cost, path = cost_path

    sum_fees = 0
    for source, target in zip(path, path[1:]):
        fee = graph[source][target]["fee"]
        sum_fees += fee
        print(f"{source} -> {target}  fee={fee} sum_fees={sum_fees}")
    assert sum_fees == cost, f"cost for this path is wrong {cost_path}"


def test_find_path_cost_wrong_bug_issue_219(graph):
    """our old implementation of find_transfer_path_sender_pays_fees failed to compute the correct cost
    for some paths

    This is a test for https://github.com/trustlines-protocol/relay/issues/219"""
    cost_path = alg.least_cost_path(
        graph=graph,
        starting_nodes={1},
        target_nodes={3},
        cost_accumulator=FeeCostAccumulator(),
    )
    sanity_check_fees(graph, cost_path)
