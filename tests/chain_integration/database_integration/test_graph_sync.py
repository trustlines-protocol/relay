from typing import cast

import pytest
from tests.chain_integration.conftest import CurrencyNetworkProxy

from relay.blockchain.currency_network_events import (
    BalanceUpdateEvent,
    BalanceUpdateEventType,
    TrustlineUpdateEvent,
    TrustlineUpdateEventType,
)
from relay.ethindex_db.ethindex_db import CurrencyNetworkEthindexDB
from relay.ethindex_db.sync_updates import (
    BalanceUpdateFeedUpdate,
    NetworkFreezeFeedUpdate,
    NetworkUnfreezeFeedUpdate,
    TrustlineUpdateFeedUpdate,
    ensure_graph_sync_id_file_exists,
    get_graph_updates_feed,
    write_graph_sync_id_file,
)
from relay.network_graph.graph import CurrencyNetworkGraph

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture(autouse=True, scope="session")
def fix_ensure_graph_sync_id_file_exists():
    ensure_graph_sync_id_file_exists()
    write_graph_sync_id_file(0)


@pytest.fixture(autouse=True)
def delete_event_feed_table(
    generic_db_connection,
    currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    currency_network_with_trustlines,
    currency_network_with_trustlines_session,
    chain_cleanup,
):
    query_string = """
        DELETE FROM graphfeed *;
    """

    with generic_db_connection:
        with generic_db_connection.cursor() as cur:
            cur.execute(query_string)


class Graph(CurrencyNetworkGraph):
    def apply_events_on_graph(self, events):
        for event in events:
            if type(event) == BalanceUpdateEvent:
                self.update_balance(event.from_, event.to, event.value, event.timestamp)
            elif type(event) == TrustlineUpdateEvent:
                self.update_trustline(
                    event.from_,
                    event.to,
                    event.creditline_given,
                    event.creditline_received,
                    event.interest_rate_given,
                    event.interest_rate_received,
                )

    def apply_feed_updates_on_graph(self, feed_updates):
        for update in feed_updates:
            self.update_from_feed(update)


def assert_equal_graphs(
    feed_graph: CurrencyNetworkGraph, event_graph: CurrencyNetworkGraph
):
    trustlines_of_feed = feed_graph.get_trustlines_list()
    trustlines_of_event = event_graph.get_trustlines_list()
    for trustline in trustlines_of_feed:
        if trustline not in trustlines_of_event:
            assert (
                False
            ), f"Found trustline in graph from feed not in graph from events {trustline}"
        else:
            feed_data = feed_graph.graph.get_edge_data(trustline[0], trustline[1])
            event_data = event_graph.graph.get_edge_data(trustline[0], trustline[1])
            assert feed_data["creditline_ab"] == event_data["creditline_ab"]
            assert feed_data["creditline_ba"] == event_data["creditline_ba"]
            assert feed_data["interest_ab"] == event_data["interest_ab"]
            assert feed_data["interest_ba"] == event_data["interest_ba"]
            assert feed_data["is_frozen"] == event_data["is_frozen"]
            assert feed_data["balance_ab"] == event_data["balance_ab"]
            if feed_data["balance_ab"] != 0:
                assert feed_data["m_time"] == event_data["m_time"]


def test_get_event_feed_trustline_update(
    currency_network: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
):
    from_ = accounts[0]
    to = accounts[1]
    creditline_given = 100
    creditline_received = 200
    interest_rate_given = 1
    interest_rate_received = 2
    currency_network.update_trustline_with_accept(
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given,
        interest_rate_received,
    )
    wait_for_ethindex_to_sync()
    feed_updates = get_graph_updates_feed(generic_db_connection)
    assert len(feed_updates) == 1
    update = feed_updates[0]
    assert type(update) == TrustlineUpdateFeedUpdate
    update = cast(TrustlineUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.creditline_received == creditline_received
    assert update.creditline_given == creditline_given
    assert update.interest_rate_given == interest_rate_given
    assert update.interest_rate_received == interest_rate_received


def test_get_event_feed_balance_update(
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
):
    currency_network = currency_network_with_trustlines_and_interests_session
    from_ = accounts[0]
    to = accounts[1]
    value = 123
    currency_network.transfer_on_path(value, [from_, to])
    wait_for_ethindex_to_sync()
    feed_updates = get_graph_updates_feed(generic_db_connection)
    assert len(feed_updates) == 1
    update = feed_updates[0]
    assert type(update) == BalanceUpdateFeedUpdate
    update = cast(BalanceUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.value == -value


def test_get_event_feed_reversed_trustline_update_to_empty(
    currency_network: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    chain,
    replace_blocks_with_empty_from_snapshot,
):
    """Test that if the chain reverts, we get a new information in the feed informing that the trustline is null"""
    from_ = accounts[0]
    to = accounts[1]
    creditline_given = 100
    creditline_received = 200
    interest_rate_given = 1
    interest_rate_received = 2
    snapshot = chain.take_snapshot()
    currency_network.update_trustline_with_accept(
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given,
        interest_rate_received,
    )
    wait_for_ethindex_to_sync()

    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)
    print("feed updates")
    for update in feed_updates:
        print(update)
        print()

    assert len(feed_updates) == 2
    update = feed_updates[0]
    assert type(update) == TrustlineUpdateFeedUpdate
    update = cast(TrustlineUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.creditline_received == creditline_received
    assert update.creditline_given == creditline_given
    assert update.interest_rate_given == interest_rate_given
    assert update.interest_rate_received == interest_rate_received

    second_update = feed_updates[1]
    assert type(second_update) == TrustlineUpdateFeedUpdate
    second_update = cast(TrustlineUpdateFeedUpdate, second_update)
    assert second_update.from_ == from_
    assert second_update.to == to
    assert second_update.creditline_received == 0
    assert second_update.creditline_given == 0
    assert second_update.interest_rate_given == 0
    assert second_update.interest_rate_received == 0


def test_get_event_feed_reversed_trustline_update_to_old(
    currency_network: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    chain,
    replace_blocks_with_empty_from_snapshot,
):
    """Test that if the chain reverts, we get a new information in the feed informing about the old trustline state"""
    from_ = accounts[0]
    to = accounts[1]
    creditline_given = 100
    creditline_received = 200
    interest_rate_given = 1
    interest_rate_received = 2

    currency_network.update_trustline_with_accept(
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given,
        interest_rate_received,
    )
    snapshot = chain.take_snapshot()
    wait_for_ethindex_to_sync()

    currency_network.update_trustline_with_accept(
        from_,
        to,
        2 * creditline_given,
        2 * creditline_received,
        2 * interest_rate_given,
        2 * interest_rate_received,
    )
    wait_for_ethindex_to_sync()
    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)
    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == TrustlineUpdateFeedUpdate
    update = cast(TrustlineUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.creditline_received == creditline_received
    assert update.creditline_given == creditline_given
    assert update.interest_rate_given == interest_rate_given
    assert update.interest_rate_received == interest_rate_received


def test_get_event_feed_reversed_balance_update_to_empty(
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    replace_blocks_with_empty_from_snapshot,
    chain,
):
    """Test that if the chain reverts a balance update, we get the information of a null balance update"""
    currency_network = currency_network_with_trustlines_and_interests_session
    from_ = accounts[0]
    to = accounts[1]
    value = 123

    snapshot = chain.take_snapshot()
    currency_network.transfer_on_path(value, [from_, to])
    wait_for_ethindex_to_sync()

    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    assert len(feed_updates) == 2
    update = feed_updates[1]
    assert type(update) == BalanceUpdateFeedUpdate
    update = cast(BalanceUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.value == 0


def test_get_event_feed_reversed_balance_update_to_old(
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    replace_blocks_with_empty_from_snapshot,
    chain,
):
    """Test that if the chain reverts a balance update, we get the information of the old balance update"""
    currency_network = currency_network_with_trustlines_and_interests_session
    from_ = accounts[0]
    to = accounts[1]
    value = 123

    currency_network.transfer_on_path(value, [from_, to])
    snapshot = chain.take_snapshot()
    wait_for_ethindex_to_sync()

    currency_network.transfer_on_path(value, [from_, to])
    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == BalanceUpdateFeedUpdate
    update = cast(BalanceUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.value == -value


def test_get_event_feed_replaced_trustline_update(
    currency_network: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    chain,
):
    """Test that if the chain reverts replacing the trustline update, we get information about the new trustline"""
    from_ = accounts[0]
    to = accounts[1]
    creditline_given = 100
    creditline_received = 200
    interest_rate_given = 1
    interest_rate_received = 2
    snapshot = chain.take_snapshot()
    currency_network.update_trustline_with_accept(
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given,
        interest_rate_received,
    )
    wait_for_ethindex_to_sync()

    chain.revert_to_snapshot(snapshot)
    currency_network.update_trustline_with_accept(
        from_,
        to,
        2 * creditline_given,
        2 * creditline_received,
        2 * interest_rate_given,
        2 * interest_rate_received,
    )
    chain.mine_block()
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == TrustlineUpdateFeedUpdate
    update = cast(TrustlineUpdateFeedUpdate, update)
    assert update.from_ == from_
    assert update.to == to
    assert update.creditline_received == 2 * creditline_received
    assert update.creditline_given == 2 * creditline_given
    assert update.interest_rate_given == 2 * interest_rate_given
    assert update.interest_rate_received == 2 * interest_rate_received


def test_get_event_feed_replaced_balance_update(
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    chain,
):
    """Test that we can revert a chain with a balance update
    and replace the balance update and still get the correct update"""
    currency_network = currency_network_with_trustlines_and_interests_session
    from_ = accounts[0]
    to = accounts[1]
    value = 123

    snapshot = chain.take_snapshot()
    currency_network.transfer_on_path(value, [from_, to])
    wait_for_ethindex_to_sync()

    chain.revert_to_snapshot(snapshot)
    currency_network.transfer_on_path(2 * value, [from_, to])
    chain.mine_block()
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    update = feed_updates[len(feed_updates) - 1]
    update = cast(BalanceUpdateFeedUpdate, update)
    assert type(update) == BalanceUpdateFeedUpdate
    assert update.from_ == from_
    assert update.to == to
    assert update.value == -2 * value


def test_get_event_feed_network_freeze(
    test_currency_network_v1: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    generic_db_connection,
):
    currency_network = test_currency_network_v1
    currency_network.freeze_network()

    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == NetworkFreezeFeedUpdate


def test_get_event_feed_network_unfreeze(
    test_currency_network_v1: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    generic_db_connection,
):
    currency_network = test_currency_network_v1
    currency_network.freeze_network()
    currency_network.unfreeze_network()

    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)
    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == NetworkUnfreezeFeedUpdate


def test_get_event_feed_reversed_network_freeze(
    test_currency_network_v1: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    generic_db_connection,
    chain,
    replace_blocks_with_empty_from_snapshot,
):
    currency_network = test_currency_network_v1

    snapshot = chain.take_snapshot()
    currency_network.freeze_network()
    wait_for_ethindex_to_sync()

    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == NetworkUnfreezeFeedUpdate


def test_get_event_feed_reversed_network_unfreeze(
    test_currency_network_v1: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    generic_db_connection,
    chain,
    replace_blocks_with_empty_from_snapshot,
):
    currency_network = test_currency_network_v1

    snapshot = chain.take_snapshot()
    currency_network.freeze_network()
    currency_network.unfreeze_network()
    wait_for_ethindex_to_sync()

    replace_blocks_with_empty_from_snapshot(snapshot)
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)

    update = feed_updates[len(feed_updates) - 1]
    assert type(update) == NetworkFreezeFeedUpdate


def sync_if_enough_transactions_sent(
    transactions_sent,
    transactions_between_sync,
    graph,
    connection,
    wait_for_ethindex_to_sync,
):
    if transactions_sent % transactions_between_sync == 0:
        wait_for_ethindex_to_sync()
        graph.apply_feed_updates_on_graph(get_graph_updates_feed(connection))


@pytest.fixture
def revert_if_enough_transactions_sent(replace_blocks_with_empty_from_snapshot):
    def revert(snapshot, transactions_sent, transactions_between_revert):
        if transactions_sent % transactions_between_revert == 0:
            return replace_blocks_with_empty_from_snapshot(snapshot)
        return snapshot

    return revert


@pytest.mark.parametrize("transactions_between_sync", [1, 2, 3, 4])
@pytest.mark.parametrize("transactions_between_revert", [1, 2, 3, 4])
def test_sync_same_graphs(
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    ethindex_db_for_currency_network_with_trustlines_and_interests: CurrencyNetworkEthindexDB,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    transactions_between_sync,
    transactions_between_revert,
    chain,
    revert_if_enough_transactions_sent,
):
    currency_network = currency_network_with_trustlines_and_interests_session
    assert get_graph_updates_feed(generic_db_connection) == []

    event_graph = Graph(
        currency_network.capacity_imbalance_fee_divisor,
        currency_network.default_interest_rate,
        currency_network.custom_interests,
        currency_network.prevent_mediator_interests,
    )
    feed_graph = Graph(
        currency_network.capacity_imbalance_fee_divisor,
        currency_network.default_interest_rate,
        currency_network.custom_interests,
        currency_network.prevent_mediator_interests,
    )

    # Make sure the feed graph starts with the proper state before getting updated with feed updates
    wait_for_ethindex_to_sync()
    events = ethindex_db_for_currency_network_with_trustlines_and_interests.get_all_contract_events(
        event_types=[BalanceUpdateEventType, TrustlineUpdateEventType]
    )
    feed_graph.apply_events_on_graph(events)

    transactions_sent = 0
    snapshot = chain.take_snapshot()

    # tx 1
    currency_network.transfer_on_path(
        123, [accounts[0], accounts[1], accounts[2], accounts[3]]
    )
    transactions_sent += 1
    sync_if_enough_transactions_sent(
        transactions_sent,
        transactions_between_sync,
        feed_graph,
        generic_db_connection,
        wait_for_ethindex_to_sync,
    )
    snapshot = revert_if_enough_transactions_sent(
        snapshot, transactions_sent, transactions_between_revert
    )

    # tx 2
    currency_network.transfer_on_path(321, [accounts[4], accounts[3], accounts[2]])
    transactions_sent += 1
    sync_if_enough_transactions_sent(
        transactions_sent,
        transactions_between_sync,
        feed_graph,
        generic_db_connection,
        wait_for_ethindex_to_sync,
    )
    snapshot = revert_if_enough_transactions_sent(
        snapshot, transactions_sent, transactions_between_revert
    )

    # tx 3
    currency_network.update_trustline_with_accept(
        accounts[0], accounts[1], 123123123, 321321321, 222, 333
    )
    transactions_sent += 1
    sync_if_enough_transactions_sent(
        transactions_sent,
        transactions_between_sync,
        feed_graph,
        generic_db_connection,
        wait_for_ethindex_to_sync,
    )
    snapshot = revert_if_enough_transactions_sent(
        snapshot, transactions_sent, transactions_between_revert
    )

    # tx 4
    currency_network.update_trustline_with_accept(
        accounts[0], accounts[1], 100000000, 200000000, 200, 300
    )
    transactions_sent += 1
    sync_if_enough_transactions_sent(
        transactions_sent,
        transactions_between_sync,
        feed_graph,
        generic_db_connection,
        wait_for_ethindex_to_sync,
    )
    snapshot = revert_if_enough_transactions_sent(
        snapshot, transactions_sent, transactions_between_revert
    )

    # tx 5
    currency_network.update_trustline_with_accept(
        accounts[0], accounts[1], 123123123, 321321321, 222, 333
    )
    revert_if_enough_transactions_sent(
        snapshot, transactions_sent, transactions_between_revert
    )

    wait_for_ethindex_to_sync()
    feed_graph.apply_feed_updates_on_graph(
        get_graph_updates_feed(generic_db_connection)
    )
    events = ethindex_db_for_currency_network_with_trustlines_and_interests.get_all_contract_events(
        event_types=[BalanceUpdateEventType, TrustlineUpdateEventType]
    )
    event_graph.apply_events_on_graph(events)

    assert_equal_graphs(feed_graph, event_graph)


def test_sync_with_reordering_of_events(
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    wait_for_ethindex_to_sync,
    accounts,
    generic_db_connection,
    chain,
):
    """Test that if we have a reordering of events with the same values, we still get a correct graph from syncing"""

    currency_network = currency_network_with_trustlines_and_interests_session
    feed_graph = Graph(
        currency_network.capacity_imbalance_fee_divisor,
        currency_network.default_interest_rate,
        currency_network.custom_interests,
        currency_network.prevent_mediator_interests,
    )

    from_ = accounts[0]
    to = accounts[1]
    credit_limit_1 = 1_000_000
    credit_limit_2 = 2_000_000

    time_1 = 2_000_000_000

    snapshot = chain.take_snapshot()
    chain.time_travel(time_1)

    currency_network_with_trustlines_and_interests_session.update_trustline_with_accept(
        from_, to, credit_limit_1, credit_limit_1
    )
    currency_network_with_trustlines_and_interests_session.update_trustline_with_accept(
        from_, to, credit_limit_2, credit_limit_2
    )

    wait_for_ethindex_to_sync()

    chain.revert_to_snapshot(snapshot)
    chain.time_travel(time_1)
    currency_network_with_trustlines_and_interests_session.update_trustline_with_accept(
        from_, to, credit_limit_2, credit_limit_2
    )
    currency_network_with_trustlines_and_interests_session.update_trustline_with_accept(
        from_, to, credit_limit_1, credit_limit_1
    )

    chain.mine_block()
    wait_for_ethindex_to_sync()

    feed_updates = get_graph_updates_feed(generic_db_connection)
    feed_graph.apply_feed_updates_on_graph(feed_updates)
    trustline_data = feed_graph.graph.get_edge_data(from_, to)

    assert trustline_data["creditline_ab"] == credit_limit_1
    assert trustline_data["creditline_ba"] == credit_limit_1


def test_sync_network_freeze_on_graph():
    feed_graph = CurrencyNetworkGraph(is_frozen=False)
    network_freeze_update = NetworkFreezeFeedUpdate(address=ZERO_ADDRESS, timestamp=0)

    assert feed_graph.is_frozen is False
    feed_graph.update_from_feed(network_freeze_update)
    assert feed_graph.is_frozen


def test_sync_network_unfreeze_on_graph():
    feed_graph = CurrencyNetworkGraph(is_frozen=True)
    network_unfreeze_update = NetworkUnfreezeFeedUpdate(
        address=ZERO_ADDRESS, timestamp=0
    )

    assert feed_graph.is_frozen
    feed_graph.update_from_feed(network_unfreeze_update)
    assert feed_graph.is_frozen is False
