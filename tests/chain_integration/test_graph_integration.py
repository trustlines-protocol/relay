import pytest
import gevent

from relay.network_graph.graph import CurrencyNetworkGraph


def link_graph(proxy, graph, full_sync_interval=None):
    if full_sync_interval is not None:
        proxy.start_listen_on_full_sync(_create_on_full_sync(graph), full_sync_interval)
    proxy.start_listen_on_balance(_create_on_balance(graph))
    proxy.start_listen_on_trustline(_create_on_trustline(graph))


def _create_on_balance(graph):
    def update_balance(event):
        graph.update_balance(event.from_, event.to, event.value)

    return update_balance


def _create_on_trustline(graph):
    def update_trustline(event):
        graph.update_trustline(event.from_,
                               event.to,
                               event.creditline_given,
                               event.creditline_received,
                               event.interest_rate_given,
                               event.interest_rate_received,
                               event.timestamp)

    return update_trustline


def _create_on_full_sync(graph):
    def update_community(graph_rep):
        graph.gen_network(graph_rep)

    return update_community


@pytest.fixture()
def community_with_trustlines(currency_network_with_trustlines):
    community = CurrencyNetworkGraph(100)
    community.gen_network(currency_network_with_trustlines.gen_graph_representation())
    link_graph(currency_network_with_trustlines, community)
    return community


@pytest.fixture()
def fresh_community(currency_network):
    community = CurrencyNetworkGraph(100)
    link_graph(currency_network, community)
    gevent.sleep(0.0001)
    return community


def test_path(community_with_trustlines, accounts):
    community = community_with_trustlines
    A, B, C, D, E, *rest = accounts
    cost, path = community.find_path(A, B, 10)
    assert path == [A, B]
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]


def test_no_capacity(community_with_trustlines, accounts):
    community = community_with_trustlines
    A, B, C, D, E, *rest = accounts
    cost, path = community.find_path(A, E, 550)
    assert path == [A, E]
    cost, path = community.find_path(A, E, 551)
    assert path == []
    cost, path = community.find_path(E, A, 500)
    assert path == [E, A]
    cost, path = community.find_path(E, A, 501)
    assert path == []


def test_trustline_update(fresh_community, currency_network, accounts):
    A, B, *rest = accounts

    currency_network.update_trustline(A, B, 50, 100, 2, 3)
    currency_network.update_trustline(B, A, 100, 50, 3, 2)

    gevent.sleep(1)

    assert fresh_community.get_account_sum(A, B).creditline_given == 50
    assert fresh_community.get_account_sum(A, B).creditline_received == 100
    assert fresh_community.get_account_sum(A, B).interest_rate_given == 2
    assert fresh_community.get_account_sum(A, B).interest_rate_received == 3


def test_transfer_update(fresh_community, currency_network, accounts):
    A, B, *rest = accounts

    currency_network.update_trustline(A, B, 50, 100)
    currency_network.update_trustline(B, A, 100, 50)
    currency_network.transfer(B, A, 20, 0, [A])

    gevent.sleep(1)

    assert fresh_community.get_account_sum(A, B).creditline_given == 50
    assert fresh_community.get_account_sum(A, B).creditline_received == 100
    assert fresh_community.get_account_sum(A, B).balance == 20
    assert fresh_community.get_account_sum(A, B).creditline_left_given == 30
    assert fresh_community.get_account_sum(A, B).creditline_left_received == 120
