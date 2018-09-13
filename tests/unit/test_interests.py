import pytest

from relay.blockchain.currency_network_proxy import Trustline
from relay.network_graph.graph import CurrencyNetworkGraph, Account

addresses = ['0x0A', '0x0B', '0x0C', '0x0D', '0x0E']
A, B, C, D, E = addresses
F = '0x0F'
G = '0x10'
H = '0x11'

creditline_ab = 'creditline_ab'
creditline_ba = 'creditline_ba'
interest_ab = 'interest_ab'
interest_ba = 'interest_ba'
fees_outstanding_a = 'fees_outstanding_a'
fees_outstanding_b = 'fees_outstanding_b'
m_time = 'm_time'
balance_ab = 'balance_ab'


@pytest.fixture
def friendsdict():
    return {A: [Trustline(B, 200, 200),
                Trustline(E, 500, 550)],
            B: [Trustline(C, 200, 250)],
            C: [Trustline(D, 300, 350)],
            D: [Trustline(E, 400, 450)],
            }


@pytest.fixture
def simple_friendsdict():
    return {A: [Trustline(B, 200, 200, interest_ba = 1000)]}


@pytest.fixture
def basic_data():
    data = {creditline_ab:0,
            creditline_ba:0,
            interest_ab:0,
            interest_ba:0,
            fees_outstanding_a:0,
            fees_outstanding_b:0,
            m_time:0,
            balance_ab:0}

    return data


@pytest.fixture
def community_with_trustlines(friendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(friendsdict)
    return community


@pytest.fixture
def community_with_simple_trustlines(simple_friendsdict):
    community = CurrencyNetworkGraph()
    community.gen_network(simple_friendsdict)
    return community


@pytest.fixture
def community_with_trustlines_and_fees(friendsdict):
    community = CurrencyNetworkGraph(100)
    community.gen_network(friendsdict)
    return community


def test_interests_calculation_from_A_balance_positive_relevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800  # at least one year ago
    data[balance_ab] = 100  # B owes to A
    data[interest_ab] = 1000  # interest given by A to B
    acc_AB = Account(data, A, B)
    assert acc_AB.balance > 101


def test_interests_calculation_from_A_balance_negative_relevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800
    data[balance_ab] = -100  # A owes to B
    data[interest_ba] = 1000  # interest given by B to A
    acc_AB = Account(data, A, B)
    assert acc_AB.balance < -101


def test_interests_calculation_from_A_balance_positive_irrelevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800
    data[balance_ab] = 100  # B owes to A
    data[interest_ba] = 1000  # interest given by B to A
    acc_AB = Account(data, A, B)
    assert acc_AB.balance == 100


def test_interests_calculation_from_A_balance_negative_irrelevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800
    data[balance_ab] = -100  # A owes to B
    data[interest_ab] = 1000  # interest given by B to A
    acc_AB = Account(data, A, B)
    assert acc_AB.balance == -100


def test_interests_calculation_from_B_balance_positive_relevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800  # at least one year ago
    data[balance_ab] = 100  # B owes to A
    data[interest_ab] = 1000  # interest given by A to B
    acc_BA = Account(data, B, A)
    assert acc_BA.balance < -101


def test_interests_calculation_from_B_balance_negative_relevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800
    data[balance_ab] = -100  # A owes to B
    data[interest_ba] = 1000  # interest given by B to A
    acc_BA = Account(data, B, A)
    assert acc_BA.balance > 101


def test_interests_calculation_from_B_balance_positive_irrelevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800
    data[balance_ab] = 100  # B owes to A
    data[interest_ba] = 1000  # interest given by B to A
    acc_BA = Account(data, B, A)
    assert acc_BA.balance == -100


def test_interests_calculation_from_B_balance_negative_irrelevant_interests(basic_data):
    data = basic_data
    data[m_time] = 1505260800
    data[balance_ab] = -100  # A owes to B
    data[interest_ab] = 1000  # interest given by B to A
    acc_BA = Account(data, B, A)
    assert acc_BA.balance == 100


def test_path_prevented_by_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab = -100, m_time = 1505260800, interest_ba=1000)]}
    # A owes to B since more than a year and has 1% interests.
    # A only has < 100 available
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(A, B, 100)
    assert path == []


def test_path_not_prevented_by_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab = -100, m_time = 1505260800, interest_ab=1000)]}
    # A owes to B since more than a year but the 1% interests are given to B not to A
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(A, B, 100)
    assert path == [A,B]


def test_path_prevented_by_interests_reverse(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab = 100, m_time = 1505260800, interest_ab=1000)]}
    # B owes to A since more than a year and has 1% interests.
    # B only has < 100 available
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(B, A, 100)
    assert path == []