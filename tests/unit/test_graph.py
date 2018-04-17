import pytest

from relay.blockchain.currency_network_proxy import Trustline
from relay.network_graph.graph import CurrencyNetworkGraph

addresses = ['0x0A', '0x0B', '0x0C', '0x0D', '0x0E']
A, B, C, D, E = addresses
F = '0x0F'
G = '0x10'


@pytest.fixture
def friendsdict():
    return {A: [Trustline(B, 100, 150),
                Trustline(E, 500, 550)],
            B: [Trustline(C, 200, 250)],
            C: [Trustline(D, 300, 350)],
            D: [Trustline(E, 400, 450)],
            }


@pytest.fixture
def simplefriendsdict():
    return {A: [Trustline(B, 5, 0)]
            }


@pytest.fixture
def complexfriendsdict():
    return {A: [Trustline(B, 50000, 50000),  # address, creditline_ab, creditline_ba
                Trustline(C, 50000, 50000)],
            B: [Trustline(D, 50000, 50000)],
            C: [Trustline(D, 50000, 50000)],
            D: [Trustline(E, 50000, 50000)],
            }


@pytest.fixture
def balances_friendsdict():
    return {A: [Trustline(B, 20, 30, balance_ab=10)],
            B: [Trustline(C, 200, 250, balance_ab=-20)]
            }


@pytest.fixture
def unsymnetricfriendsdict():
    return {A: [Trustline(B, 2, 5, 0)]
            }


@pytest.fixture
def community_with_trustlines(friendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(friendsdict)
    return community


@pytest.fixture
def community_with_trustlines_and_fees(friendsdict):
    community = CurrencyNetworkGraph(100)
    community.gen_network(friendsdict)
    return community


@pytest.fixture
def balances_community(balances_friendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(balances_friendsdict)
    return community


@pytest.fixture
def complex_community_with_trustlines_and_fees(complexfriendsdict):
    community = CurrencyNetworkGraph(100)
    community.gen_network(complexfriendsdict)
    return community


def test_users(community_with_trustlines):
    community = community_with_trustlines
    assert len(community.users) == 5  # should have 5 users
    assert len(set(community.users) & set(addresses)) == 5  # all users should be in the graph


def test_friends(community_with_trustlines):
    community = community_with_trustlines
    assert A in community.get_friends(B)  # test friends of B
    assert C in community.get_friends(B)


def test_account(community_with_trustlines):
    community = community_with_trustlines
    account = community.get_account_sum(D, C)
    assert account.balance == 0
    assert account.creditline_given == 350
    assert account.creditline_received == 300


def test_account_sum(community_with_trustlines):
    community = community_with_trustlines
    account = community.get_account_sum(A)
    assert account.balance == 0
    assert account.creditline_given == 600
    assert account.creditline_received == 700


def test_update_trustline(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B, A).creditline_received == 100
    community.update_creditline(A, B, 200)
    assert community.get_account_sum(B, A).creditline_received == 200


def test_update_balance(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B).balance == 0
    community.update_balance(A, B, 20)
    community.update_balance(B, C, 10)
    assert community.get_account_sum(B).balance == -10


def test_transfer(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B).balance == 0
    community.transfer(A, B, 100)
    assert community.get_account_sum(B).balance == 100


def test_mediated_transfer(community_with_trustlines):
    community = community_with_trustlines
    community.mediated_transfer(A, C, 50)
    assert community.get_account_sum(A).balance == -50
    assert community.get_account_sum(B).balance == 0
    assert community.get_account_sum(C).balance == 50
    assert community.get_account_sum(A, B).balance == -50
    assert community.get_account_sum(B, C).balance == -50


def test_spent(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A).creditline_left_received == 700
    community.transfer(A, B, 70)
    assert community.get_account_sum(A).creditline_left_received == 630
    community.transfer(E, A, 20)
    assert community.get_account_sum(A).creditline_left_received == 650


def test_path(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, B, 10)
    assert path == [A, B]
    assert cost == 0
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]
    assert cost == 0


def test_no_path(community_with_trustlines):
    community = community_with_trustlines
    community.update_creditline(F, G, 100)
    cost, path = community.find_path(G, F, 10)
    assert path == [G, F]
    cost, path = community.find_path(A, G, 10)  # no path at all
    assert path == []


def test_no_capacity(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, E, 550)
    assert path == [A, E]
    cost, path = community.find_path(A, E, 551)
    assert path == []
    cost, path = community.find_path(E, A, 500)
    assert path == [E, A]
    cost, path = community.find_path(E, A, 501)
    assert path == []


def test_no_direction(community_with_trustlines):
    community = community_with_trustlines
    community.update_creditline(F, G, 100)
    cost, path = community.find_path(G, F, 10)
    assert path == [G, F]
    cost, path = community.find_path(F, G, 10)  # no creditline in this direction
    assert path == []


def test_valid_path_raises_no_value_error(complex_community_with_trustlines_and_fees):
    """Verifies that the condition for raising a ValueError is not faulty
    see https://github.com/trustlines-network/relay/issues/91"""
    complex_community_with_trustlines_and_fees.update_balance(A, B, -10000)  # amount B owes A because A < B
    complex_community_with_trustlines_and_fees.update_balance(A, C, 10000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, -10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 10000)
    complex_community_with_trustlines_and_fees.update_balance(D, E, 0)
    cost, path = complex_community_with_trustlines_and_fees.find_path(E, A, 10000)  # should not raise ValueError


def test_max_hops(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]
    cost, path = community.find_path(A, D, 10, max_hops=1)
    assert path == []


def test_send_back(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A, B).balance == 0
    assert community.find_path(B, A, 120)[1] == [B, C, D, E, A]
    assert community.find_path(A, B, 120)[1] == [A, B]
    community.mediated_transfer(A, B, 120)
    assert community.get_account_sum(B, A).balance == 120
    assert community.find_path(B, A, 120)[1] == [B, A]
    assert community.find_path(A, B, 120)[1] == [A, E, D, C, B]
    community.mediated_transfer(B, A, 120)
    assert community.get_account_sum(A, B).balance == 0


def test_send_more(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 150
    assert community.get_account_sum(B, A).creditline_left_received == 100
    assert community.find_path(A, B, 120)[1] == [A, B]
    assert community.find_path(B, A, 120)[1] == [B, C, D, E, A]
    community.mediated_transfer(A, B, 120)
    assert community.get_account_sum(B, A).balance == 120
    assert community.get_account_sum(B, A).creditline_left_received == 220
    assert community.find_path(A, B, 200)[1] == [A, E, D, C, B]
    assert community.find_path(B, A, 200)[1] == [B, A]
    community.mediated_transfer(B, A, 200)
    assert community.get_account_sum(A, B).balance == 80


def test_send_more_nopath(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 150
    assert community.get_account_sum(B, A).creditline_left_received == 100
    assert community.find_path(A, B, 160)[1] == [A, E, D, C, B]
    assert community.find_path(B, A, 160)[1] == [B, C, D, E, A]
    community.mediated_transfer(A, B, 50)
    assert community.get_account_sum(B, A).balance == 50
    assert community.get_account_sum(A, B).creditline_left_received == 100
    assert community.get_account_sum(B, A).creditline_left_received == 150
    assert community.find_path(A, B, 160)[1] == [A, E, D, C, B]
    assert community.find_path(B, A, 160)[1] == [B, C, D, E, A]
    community.mediated_transfer(B, A, 50)
    assert community.get_account_sum(A, B).balance == 0


def test_no_money_created(community_with_trustlines):
    community = community_with_trustlines
    assert community.money_created == 0


def test_money_created(balances_community):
    community = balances_community
    assert community.money_created == 30


def test_no_creditlines():
    community = CurrencyNetworkGraph()
    assert community.total_creditlines == 0


def test_total_creditlines(balances_community):
    community = balances_community
    assert community.total_creditlines == 500


def test_transfer_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    assert community.get_account_sum(B).balance == 0
    community.transfer(A, B, 100)
    assert community.get_account_sum(B).balance == 100 + 2


def test_mediated_transfer_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    community.mediated_transfer(A, C, 50)
    assert community.get_account_sum(A).balance == -50 + -2
    assert community.get_account_sum(B).balance == 0 + 1
    assert community.get_account_sum(C).balance == 50 + 1
    assert community.get_account_sum(A, B).balance == -50 + -2
    assert community.get_account_sum(B, C).balance == -50 + -1


def test_path_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_path(A, B, 10)
    assert path == [A, B]
    assert cost == 1
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]
    assert cost == 2


def test_max_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_path(A, D, 110)
    assert path == [A, E, D]
    assert cost == 4
    cost, path = community.find_path(A, D, 110, max_fees=3)
    assert path == []


def test_no_capacity_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_path(A, E, 544)
    assert path == [A, E]
    cost, path = community.find_path(A, E, 545)
    assert path == []
    cost, path = community.find_path(E, A, 495)
    assert path == [E, A]
    cost, path = community.find_path(E, A, 496)
    assert path == []


def test_send_back_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    assert community.get_account_sum(A, B).balance == 0
    assert community.find_path(B, A, 120)[1] == [B, C, D, E, A]
    assert community.find_path(A, B, 120)[1] == [A, B]
    assert community.mediated_transfer(A, B, 120) == 2
    assert community.get_account_sum(B, A).balance == 120 + 2
    assert community.find_path(B, A, 120)[1] == [B, A]
    assert community.find_path(A, B, 120)[1] == [A, E, D, C, B]
    assert community.mediated_transfer(B, A, 120) == 0
    assert community.get_account_sum(A, B).balance == 0 - 2


def test_send_more_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 150
    assert community.get_account_sum(B, A).creditline_left_received == 100
    assert community.find_path(A, B, 120)[1] == [A, B]
    assert community.find_path(B, A, 120)[1] == [B, C, D, E, A]
    assert community.mediated_transfer(A, B, 120) == 2
    assert community.get_account_sum(B, A).balance == 120 + 2
    assert community.get_account_sum(B, A).creditline_left_received == 220 + 2
    assert community.find_path(A, B, 200)[1] == []
    assert community.find_path(B, A, 200)[1] == [B, A]
    assert community.mediated_transfer(B, A, 200) == 1
    assert community.get_account_sum(A, B).balance == 80 - 2 + 1
