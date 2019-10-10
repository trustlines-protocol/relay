import time

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
        graph.update_trustline(
            event.from_,
            event.to,
            event.creditline_given,
            event.creditline_received,
            event.interest_rate_given,
            event.interest_rate_received,
        )

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
    cost, path = community.find_transfer_path_sender_pays_fees(A, B, 10)
    assert path == [A, B]
    cost, path = community.find_transfer_path_sender_pays_fees(A, D, 10)
    assert path == [A, E, D]


def test_no_capacity(community_with_trustlines, accounts):
    community = community_with_trustlines
    A, B, C, D, E, *rest = accounts
    cost, path = community.find_transfer_path_sender_pays_fees(A, E, 550)
    assert path == [A, E]
    cost, path = community.find_transfer_path_sender_pays_fees(A, E, 551)
    assert path == []
    cost, path = community.find_transfer_path_sender_pays_fees(E, A, 500)
    assert path == [E, A]
    cost, path = community.find_transfer_path_sender_pays_fees(E, A, 501)
    assert path == []


def test_trustline_update(fresh_community, currency_network, accounts):
    A, B, *rest = accounts

    currency_network.update_trustline(A, B, 50, 100, 2, 3)
    currency_network.update_trustline(B, A, 100, 50, 3, 2)

    gevent.sleep(1)

    account_sum = fresh_community.get_account_sum(A, B, timestamp=int(time.time()))
    assert account_sum.creditline_given == 50
    assert account_sum.creditline_received == 100
    assert account_sum.interest_rate_given == 2
    assert account_sum.interest_rate_received == 3


def test_transfer_update(fresh_community, currency_network, accounts):
    A, B, *rest = accounts

    currency_network.update_trustline(A, B, 50, 100)
    currency_network.update_trustline(B, A, 100, 50)
    currency_network.transfer(B, A, 20, 0, [A])

    gevent.sleep(1)

    account_sum = fresh_community.get_account_sum(A, B, timestamp=int(time.time()))
    assert account_sum.creditline_given == 50
    assert account_sum.creditline_received == 100
    assert account_sum.balance == 20
    assert account_sum.creditline_left_given == 30
    assert account_sum.creditline_left_received == 120


def test_pending_block_path_bug_698(
    fresh_community, currency_network, currency_network_contract, accounts, chain
):
    """
    Tests that we can query for path with a graph updated by the pending block.
    The bug in https://github.com/trustlines-network/project/issues/698 made explicit that getting max capacity path
    works with the pending block view and getting a path did not.
    This test ensures it now works.
    """
    A, B, *rest = accounts
    credit_limit = 50
    transfer_value = 25

    currency_network.update_trustline(A, B, credit_limit, credit_limit)
    currency_network.update_trustline(B, A, credit_limit, credit_limit)

    chain.disable_auto_mine_transactions()

    # I avoid using the currency network proxy as it will wait for transaction receipt and we do not mine blocks
    # So waiting for transaction receipt will wait forever
    currency_network_contract.functions.transfer(
        B, transfer_value, 10, [B], b""
    ).transact({"from": A})
    gevent.sleep(1)

    # sanity test that the graph view was updated and we can find path and max capacity path
    max_value, max_path = fresh_community.find_maximum_capacity_path(B, A)
    assert max_value == credit_limit + transfer_value
    value, path = fresh_community.find_transfer_path_sender_pays_fees(B, A, max_value)
    assert path == max_path

    # This should not raise an eth_tester.exceptions.TransactionFailed error
    currency_network.estimate_gas_for_transfer(B, A, max_value, 10, path[1:])
