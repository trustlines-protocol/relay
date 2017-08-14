import pytest

from relay.graph import Friendship, CurrencyNetworkGraph

addresses = ['0x0A', '0x0B', '0x0C', '0x0D', '0x0E']
A, B, C, D, E = addresses
F = '0x0F'
G = '0x10'


@pytest.fixture
def friendsdict():
    return {A: [Friendship(B, 100, 150, 0),
                Friendship(E, 500, 550, 0)],
            B: [Friendship(C, 200, 250, 0)],
            C: [Friendship(D, 300, 350, 0)],
            D: [Friendship(E, 400, 450, 0)],
            }


@pytest.fixture
def simplefriendsdict():
    return {A: [Friendship(B, 5, 0 , 0)]
            }


@pytest.fixture
def balances_friendsdict():
    return {A: [Friendship(B, 20, 30 , 10)],
            B: [Friendship(C, 200, 250, -20)]
            }


@pytest.fixture
def unsymnetricfriendsdict():
    return {A: [Friendship(B, 2, 5 , 0)]
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
    assert account.trustline_given == 350
    assert account.trustline_received == 300


def test_account_sum(community_with_trustlines):
    community = community_with_trustlines
    account = community.get_account_sum(A)
    assert account.balance == 0
    assert account.trustline_given == 600
    assert account.trustline_received == 700


def test_update_trustline(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B, A).trustline_received == 100
    community.update_trustline(A, B, 200)
    assert community.get_account_sum(B, A).trustline_received == 200


def test_update_balance(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B).balance == 0
    community.update_balance(A, B, 20)
    community.update_balance(B, C, 10)
    assert community.get_account_sum(B).balance == -10


def test_transfer(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B).balance == 0
    community.transfer(A, B, 20)
    assert community.get_account_sum(B).balance == 20


def test_mediated_transfer(community_with_trustlines):
    community = community_with_trustlines
    community.mediated_transfer(A, C, 100)
    assert community.get_account_sum(A).balance == -100
    assert community.get_account_sum(B).balance == 0
    assert community.get_account_sum(C).balance == 100
    assert community.get_account_sum(A, B).balance == -100
    assert community.get_account_sum(B, C).balance == -100


def test_spent(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A).trustline_left_received == 700
    community.transfer(A, B, 70)
    assert community.get_account_sum(A).trustline_left_received == 630
    community.transfer(E, A, 20)
    assert community.get_account_sum(A).trustline_left_received == 650


def test_path(community_with_trustlines):
    community = community_with_trustlines
    path = community.find_path(A, B, 10)
    assert path == [A, B]
    path = community.find_path(A, D, 10)
    assert path == [A, E, D]


def test_no_path(community_with_trustlines):
    community = community_with_trustlines
    community.update_trustline(F, G, 100)
    path = community.find_path(G, F, 100)
    assert path == [G, F]
    path = community.find_path(A, G, 10)  # no path at all
    assert path == []


def test_no_capacity(community_with_trustlines):
    community = community_with_trustlines
    path = community.find_path(A, E, 550)
    assert path == [A, E]
    path = community.find_path(A, E, 551)
    assert path == []
    path = community.find_path(E, A, 500)
    assert path == [E, A]
    path = community.find_path(E, A, 501)
    assert path == []


def test_no_direction(community_with_trustlines):
    community = community_with_trustlines
    community.update_trustline(F, G, 100)
    path = community.find_path(G, F, 10)
    assert path == [G, F]
    path = community.find_path(F, G, 10)  # no trustline in this direction
    assert path == []


def test_send_back(simple_community):
    community = simple_community
    assert community.get_account_sum(A, B).balance == 0
    assert community.find_path(A, B, 1) == []
    assert community.find_path(B, A, 1) == [B, A]
    assert community.mediated_transfer(B, A, 1)
    assert community.get_account_sum(A, B).balance == 1
    assert community.find_path(A, B, 1) == [A, B]
    assert community.find_path(B, A, 1) == [B, A]
    assert community.mediated_transfer(A, B, 1)
    assert community.get_account_sum(A, B).balance == 0


def test_send_more(unsymmetric_community):
    community = unsymmetric_community
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).trustline_left_received == 5
    assert community.get_account_sum(B, A).trustline_left_received == 2
    assert community.find_path(A, B, 5) == [A, B]
    assert community.find_path(B, A, 2) == [B, A]
    assert community.mediated_transfer(A, B, 3)
    assert community.get_account_sum(B, A).balance == 3
    assert community.get_account_sum(B, A).trustline_left_received == 5
    assert community.find_path(A, B, 2) == [A, B]
    assert community.find_path(B, A, 5) == [B, A]
    assert community.mediated_transfer(B, A, 5)
    assert community.get_account_sum(A, B).balance == 2


def test_send_more_nopath(unsymmetric_community):
    community = unsymmetric_community
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).trustline_left_received == 5
    assert community.get_account_sum(B, A).trustline_left_received == 2
    assert community.find_path(A, B, 5.1) == []
    assert community.find_path(B, A, 2.1) == []
    assert community.mediated_transfer(A, B, 3)
    assert community.get_account_sum(B, A).balance == 3
    assert community.get_account_sum(B, A).trustline_left_received == 5
    assert community.find_path(A, B, 2.1) == []
    assert community.find_path(B, A, 5.1) == []
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