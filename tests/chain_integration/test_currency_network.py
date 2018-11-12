import gevent

from relay.blockchain.currency_network_events import (
    TrustlineRequestEventType,
    TrustlineUpdateEventType,
    TransferEventType
)


def context_switch():
    gevent.sleep(0.01)


def test_decimals(currency_network):
    assert currency_network.decimals == 6


def test_name(currency_network):
    assert currency_network.name == 'Trustlines'


def test_symbol(currency_network):
    assert currency_network.symbol == 'T'


def test_address(currency_network, testnetwork1_address):
    assert currency_network.address == testnetwork1_address


def test_friends1(currency_network_with_trustlines, accounts):
    assert set(currency_network_with_trustlines.friends(accounts[0])) == {accounts[1], accounts[4]}


def test_friends2(currency_network_with_trustlines, accounts):
    assert set(currency_network_with_trustlines.friends(accounts[1])) == {accounts[0], accounts[2]}


def test_account1(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.account(accounts[0], accounts[1]) == [100, 150, 0, 0, 0, 0, 0, 0]


def test_account2(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.account(accounts[2], accounts[3]) == [300, 350, 0, 0, 0, 0, 0, 0]


def test_users(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.users == accounts


def test_spendable(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.spendable(accounts[1]) == 350


def test_spendable_to(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.spendableTo(accounts[3], accounts[4]) == 450


def test_gen_graph_representation(currency_network_with_trustlines, accounts):
    graph_representation = currency_network_with_trustlines.gen_graph_representation()

    for account in accounts:
        assert (account in graph_representation)


def test_number_of_get_events(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    assert len(currency_network.get_network_events(TrustlineRequestEventType, user_address=accounts[0])) == 3
    assert len(currency_network.get_network_events(TrustlineUpdateEventType, user_address=accounts[0])) == 3
    assert len(currency_network.get_network_events(TransferEventType, user_address=accounts[0])) == 1


def test_get_events(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    creditline_update_events = currency_network.get_network_events(TrustlineUpdateEventType, user_address=accounts[0])
    e1, e2, e3 = creditline_update_events
    assert (e1.counter_party, e2.counter_party, e3.counter_party) == (accounts[1], accounts[2], accounts[4])


def test_get_transfer_event(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    transfer_event = currency_network.get_network_events(TransferEventType, user_address=accounts[0])[0]
    assert transfer_event.value == 10
    assert transfer_event.to == accounts[0]
    assert transfer_event.from_ == accounts[1]
    assert transfer_event.user == accounts[0]
    assert transfer_event.counter_party == accounts[1]
    assert transfer_event.direction == 'received'


def test_number_of_get_all_events(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    assert len(currency_network.get_all_network_events(user_address=accounts[0])) == 7


def test_listen_on_balance_update(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    currency_network.start_listen_on_balance(f)
    context_switch()
    currency_network.update_trustline_with_accept(accounts[0], accounts[1], 25, 50)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    gevent.sleep(1)

    assert len(events) == 1
    assert (events[0].from_ == accounts[0] or events[0].from_ == accounts[1])
    assert (events[0].to == accounts[0] or events[0].to == accounts[1])
    assert (-12 < events[0].value < 12)  # because there might be fees


def test_listen_on_transfer(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    currency_network.start_listen_on_transfer(f)
    context_switch()
    currency_network.update_trustline_with_accept(accounts[0], accounts[1], 25, 50)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0].from_ == accounts[1]
    assert events[0].to == accounts[0]
    assert events[0].value == 10


def test_listen_on_trustline_update(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    currency_network.start_listen_on_trustline(f)
    context_switch()
    currency_network.update_trustline(accounts[0], accounts[1], 25, 50)
    currency_network.update_trustline(accounts[1], accounts[0], 50, 25)
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0].from_ == accounts[0]
    assert events[0].to == accounts[1]
    assert events[0].creditline_given == 25
    assert events[0].creditline_received == 50


def test_listen_on_trustline_update_with_interests(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    currency_network.start_listen_on_trustline(f)
    context_switch()
    currency_network.update_trustline(accounts[0], accounts[1], 25, 50, 2, 3)
    currency_network.update_trustline(accounts[1], accounts[0], 50, 25, 3, 2)
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0].from_ == accounts[0]
    assert events[0].to == accounts[1]
    assert events[0].creditline_given == 25
    assert events[0].creditline_received == 50
    assert events[0].interest_rate_given == 2
    assert events[0].interest_rate_received == 3
