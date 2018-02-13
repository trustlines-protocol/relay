import pytest

from relay.network_graph.graph import CurrencyNetworkGraph


@pytest.fixture()
def community_with_trustlines(currency_network_with_trustlines):
    community = CurrencyNetworkGraph(100)
    community.gen_network(currency_network_with_trustlines.gen_graph_representation())
    return community


def test_path(community_with_trustlines, accounts):
    community = community_with_trustlines
    A, B, C, D, E = accounts
    cost, path = community.find_path(A, B, 10)
    assert path == [A, B]
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]


def test_no_capacity(community_with_trustlines, accounts):
    community = community_with_trustlines
    A, B, C, D, E = accounts
    cost, path = community.find_path(A, E, 544)
    assert path == [A, E]
    cost, path = community.find_path(A, E, 545)
    assert path == []
    cost, path = community.find_path(E, A, 495)
    assert path == [E, A]
    cost, path = community.find_path(E, A, 496)
    assert path == []
