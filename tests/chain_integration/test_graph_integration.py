import pytest
import gevent

from relay.network_graph.graph import CurrencyNetworkGraph
from relay.main import link_graph


@pytest.fixture()
def community_with_trustlines(currency_network_with_trustlines):
    community = CurrencyNetworkGraph(100)
    community.gen_network(currency_network_with_trustlines.gen_graph_representation())
    link_graph(currency_network_with_trustlines, community)
    return community


@pytest.fixture()
def fresh_community(fresh_currency_network):
    community = CurrencyNetworkGraph(100)
    link_graph(fresh_currency_network, community)
    gevent.sleep(0.0001)
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


def test_creditline_update(fresh_community, fresh_currency_network, accounts):
    A, B, *rest = accounts

    fresh_currency_network.update_creditline(A, B, 50)
    fresh_currency_network.accept_creditline(B, A, 50)

    gevent.sleep(1)

    assert fresh_community.get_account_sum(A, B).creditline_given == 50
    assert fresh_community.get_account_sum(A, B).creditline_received == 0


def test_trustline_update(fresh_community, fresh_currency_network, accounts):
    A, B, *rest = accounts

    fresh_currency_network.update_trustline(A, B, 50, 100)
    fresh_currency_network.update_trustline(B, A, 100, 50)

    gevent.sleep(1)

    assert fresh_community.get_account_sum(A, B).creditline_given == 50
    assert fresh_community.get_account_sum(A, B).creditline_received == 100


def test_transfer_update(fresh_community, fresh_currency_network, accounts):
    A, B, *rest = accounts

    fresh_currency_network.update_trustline(A, B, 50, 100)
    fresh_currency_network.update_trustline(B, A, 100, 50)
    fresh_currency_network.transfer(B, A, 20, 1, [A])

    gevent.sleep(1)

    assert fresh_community.get_account_sum(A, B).creditline_given == 50
    assert fresh_community.get_account_sum(A, B).creditline_received == 100
    assert fresh_community.get_account_sum(A, B).balance == 21
    assert fresh_community.get_account_sum(A, B).creditline_left_given == 29
    assert fresh_community.get_account_sum(A, B).creditline_left_received == 121
