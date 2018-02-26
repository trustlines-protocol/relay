import gevent

from relay.blockchain.currency_network_proxy import CreditlineUpdatedEvent, CreditlineRequestEvent, TransferEvent


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
    assert len(currency_network.get_network_events(CreditlineUpdatedEvent, user_address=accounts[0])) == 3
    assert len(currency_network.get_network_events(CreditlineRequestEvent, user_address=accounts[0])) == 3
    assert len(currency_network.get_network_events(TransferEvent, user_address=accounts[0])) == 1


def test_number_of_get_all_events(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    assert len(currency_network.get_all_network_events(user_address=accounts[0])) == 7


def test_listen_on_creditline_update(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, value):
        events.append((from_, to, value))

    currency_network.start_listen_on_creditline(f)
    context_switch()
    currency_network.update_creditline(accounts[0], accounts[1], 25)
    currency_network.accept_creditline(accounts[1], accounts[0], 25)
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0] == (accounts[0], accounts[1], 25)


def test_listen_on_balance_update(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, value):
        events.append((from_, to, value))

    currency_network.start_listen_on_balance(f)
    context_switch()
    currency_network.update_creditline(accounts[0], accounts[1], 25)
    currency_network.accept_creditline(accounts[1], accounts[0], 25)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    gevent.sleep(1)

    assert len(events) == 1
    assert (events[0][0] == accounts[0] or events[0][0] == accounts[1])
    assert (events[0][1] == accounts[0] or events[0][1] == accounts[1])
    assert (-12 < events[0][2] < 12)  # because there might be fees


def test_listen_on_transfer(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, value):
        events.append((from_, to, value))

    currency_network.start_listen_on_transfer(f)
    context_switch()
    currency_network.update_creditline(accounts[0], accounts[1], 25)
    currency_network.accept_creditline(accounts[1], accounts[0], 25)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0] == (accounts[1], accounts[0], 10)


def test_listen_on_trustline_update(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, given, received):
        events.append((from_, to, given, received))

    currency_network.start_listen_on_trustline(f)
    context_switch()
    currency_network.update_trustline(accounts[0], accounts[1], 25, 50)
    currency_network.update_trustline(accounts[1], accounts[0], 50, 25)
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0] == (accounts[1], accounts[0], 50, 25)
