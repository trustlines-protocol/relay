import pytest

import networkx as nx
from relay.network_graph.dijkstra_weighted import find_path


@pytest.fixture()
def graph():
    g = nx.Graph()
    for i in range(5, 40):
        g.add_edge(i, i + 1, fee=100)

    g.add_edge(7, 20, fee=100)
    g.add_edge(19, 32, fee=100)

    g.add_edge(5, 15, fee=1)
    g.add_edge(15, 16, fee=1)
    g.add_edge(16, 17, fee=1)
    g.add_edge(17, 18, fee=1)
    g.add_edge(18, 19, fee=1)
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


def test_find_path_cost_wrong_bug(graph):
    """our current implementation fails to compute the correct cost for some
    paths"""
    cost_path = find_path(
        graph, source=5, target=32, get_fee=lambda e, u, v, d: e["fee"], value=0
    )
    sanity_check_fees(graph, cost_path)
