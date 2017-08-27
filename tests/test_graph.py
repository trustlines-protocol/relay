import pytest

from relay.graph import CurrencyNetworkGraph
from relay.currency_network import Trustline


addresses = ['0x0A', '0x0B', '0x0C', '0x0D', '0x0E']
A, B, C, D, E = addresses
F = '0x0F'
G = '0x10'


@pytest.fixture
def friendsdict():
    return {A: [Trustline(B, 100, 150, 0),
                Trustline(E, 500, 550, 0)],
            B: [Trustline(C, 200, 250, 0)],
            C: [Trustline(D, 300, 350, 0)],
            D: [Trustline(E, 400, 450, 0)],
            }


@pytest.fixture
def simplefriendsdict():
    return {A: [Trustline(B, 5, 0, 0)]
            }


@pytest.fixture
def balances_friendsdict():
    return {A: [Trustline(B, 20, 30 , 10)],
            B: [Trustline(C, 200, 250, -20)]
            }


@pytest.fixture
def unsymnetricfriendsdict():
    return {A: [Trustline(B, 2, 5 , 0)]
            }


@pytest.fixture
def community_with_trustlines(friendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(friendsdict)
    return community


@pytest.fixture
def simple_community(simplefriendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(simplefriendsdict)
    return community


@pytest.fixture
def unsymmetric_community(unsymnetricfriendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(unsymnetricfriendsdict)
    return community


@pytest.fixture
def balances_community(balances_friendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(balances_friendsdict)
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
    assert community.get_account_sum(B).balance == 100 + 2


def test_mediated_transfer(community_with_trustlines):
    community = community_with_trustlines
    community.mediated_transfer(A, C, 50)
    assert community.get_account_sum(A).balance == -50 + -2
    assert community.get_account_sum(B).balance == 0 + 1
    assert community.get_account_sum(C).balance == 50 + 1
    assert community.get_account_sum(A, B).balance == -50 + -2
    assert community.get_account_sum(B, C).balance == -50 + -1


def test_spent(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A).creditline_left_received == 700
    community.transfer(A, B, 70)
    assert community.get_account_sum(A).creditline_left_received == 630 - 1
    community.transfer(E, A, 20)
    assert community.get_account_sum(A).creditline_left_received == 650


def test_path(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, B, 10)
    assert path == [A, B]
    assert cost == 1
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]
    assert cost == 2


def test_no_path(community_with_trustlines):
    community = community_with_trustlines
    community.update_creditline(F, G, 100)
    cost, path = community.find_path(G, F, 10)
    assert path == [G, F]
    cost, path = community.find_path(A, G, 10)  # no path at all
    assert path == []


def test_no_capacity(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, E, 544)
    assert path == [A, E]
    cost, path = community.find_path(A, E, 545)
    assert path == []
    cost, path = community.find_path(E, A, 495)
    assert path == [E, A]
    cost, path = community.find_path(E, A, 496)
    assert path == []


def test_no_direction(community_with_trustlines):
    community = community_with_trustlines
    community.update_creditline(F, G, 100)
    cost, path = community.find_path(G, F, 10)
    assert path == [G, F]
    cost, path = community.find_path(F, G, 10)  # no creditline in this direction
    assert path == []


def test_max_hops(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, D, 10)
    assert path == [A, E, D]
    cost, path = community.find_path(A, D, 10, max_hops=1)
    assert path == []


def test_max_fees(community_with_trustlines):
    community = community_with_trustlines
    cost, path = community.find_path(A, D, 110)
    assert path == [A, E, D]
    assert cost == 4
    cost, path = community.find_path(A, D, 110, max_fees=3)
    assert path == []


def test_send_back(simple_community):
    community = simple_community
    assert community.get_account_sum(A, B).balance == 0
    assert community.find_path(A, B, 1)[1] == []
    assert community.find_path(B, A, 1)[1] == [B, A]
    assert community.mediated_transfer(B, A, 1) == 1
    assert community.get_account_sum(A, B).balance == 1 + 1
    assert community.find_path(A, B, 1)[1] == [A, B]
    assert community.find_path(B, A, 1)[1] == [B, A]
    assert community.mediated_transfer(A, B, 1) == 0
    assert community.get_account_sum(A, B).balance == 0 + 1


def test_send_more(unsymmetric_community):
    community = unsymmetric_community
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 5
    assert community.get_account_sum(B, A).creditline_left_received == 2
    assert community.find_path(A, B, 4)[1] == [A, B]
    assert community.find_path(B, A, 1)[1] == [B, A]
    assert community.mediated_transfer(A, B, 2) == 1
    assert community.get_account_sum(B, A).balance == 3
    assert community.get_account_sum(B, A).creditline_left_received == 5
    assert community.find_path(A, B, 1)[1] == [A, B]
    assert community.find_path(B, A, 4)[1] == [B, A]
    assert community.mediated_transfer(B, A, 4)
    assert community.get_account_sum(A, B).balance == 2


def test_send_more_nopath(unsymmetric_community):
    community = unsymmetric_community
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 5
    assert community.get_account_sum(B, A).creditline_left_received == 2
    assert community.find_path(A, B, 5)[1] == []
    assert community.find_path(B, A, 3)[1] == []
    assert community.mediated_transfer(A, B, 3)
    assert community.get_account_sum(B, A).balance == 4
    assert community.get_account_sum(B, A).creditline_left_received == 6
    assert community.find_path(A, B, 3)[1] == []
    assert community.find_path(B, A, 6)[1] == []
    assert community.mediated_transfer(B, A, 5)
    assert community.get_account_sum(A, B).balance == 2


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