import gevent


def context_switch():
    gevent.sleep(0.01)


def test_decimals(currency_network):
    assert currency_network.decimals == 6


def test_name(currency_network):
    assert currency_network.name == "Trustlines"


def test_symbol(currency_network):
    assert currency_network.symbol == "T"


def test_address(currency_network, testnetwork1_address):
    assert currency_network.address == testnetwork1_address


def test_friends1(currency_network_with_trustlines, accounts):
    assert set(currency_network_with_trustlines.fetch_friends(accounts[0])) == {
        accounts[1],
        accounts[4],
    }


def test_friends2(currency_network_with_trustlines, accounts):
    assert set(currency_network_with_trustlines.fetch_friends(accounts[1])) == {
        accounts[0],
        accounts[2],
    }


def test_account1(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.fetch_account(accounts[0], accounts[1]) == [
        100,
        150,
        0,
        0,
        False,
        0,
        0,
    ]


def test_account2(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.fetch_account(accounts[2], accounts[3]) == [
        300,
        350,
        0,
        0,
        False,
        0,
        0,
    ]


def test_users(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.fetch_users() == accounts[0:7]


def test_is_frozen(currency_network, chain):
    assert currency_network.fetch_is_frozen_status() is False
    currency_network.time_travel_to_expiration(chain)
    currency_network._proxy.functions.freezeNetwork().transact()
    assert currency_network.fetch_is_frozen_status() is True


def test_gen_graph_representation(currency_network_with_trustlines, accounts):
    graph_representation = currency_network_with_trustlines.gen_graph_representation()

    for account in accounts[0:5]:
        assert account in (trustline.user for trustline in graph_representation) or (
            account in (trustline.counter_party for trustline in graph_representation)
        )


def test_listen_on_transfer(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    greenlet = currency_network.start_listen_on_transfer(f)
    context_switch()
    currency_network.update_trustline_with_accept(accounts[0], accounts[1], 25, 50)
    currency_network.transfer(accounts[1], 10, 10, [accounts[1], accounts[0]])
    gevent.sleep(1)

    print(events)
    assert len(events) == 1
    assert events[0].from_ == accounts[1]
    assert events[0].to == accounts[0]
    assert events[0].value == 10

    greenlet.kill()


def test_listen_on_trustline_update(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    greenlet = currency_network.start_listen_on_trustline(f)
    context_switch()
    currency_network.update_trustline(accounts[0], accounts[1], 25, 50)
    currency_network.update_trustline(accounts[1], accounts[0], 50, 25)
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0].from_ == accounts[0]
    assert events[0].to == accounts[1]
    assert events[0].creditline_given == 25
    assert events[0].creditline_received == 50
    assert events[0].is_frozen is False

    greenlet.kill()


def test_listen_on_trustline_update_with_interests(currency_network, accounts):
    events = []

    def f(event):
        events.append(event)

    greenlet = currency_network.start_listen_on_trustline(f)
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
    assert events[0].is_frozen is False

    greenlet.kill()
