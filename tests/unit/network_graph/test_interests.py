import pytest
import math

from relay.blockchain.currency_network_proxy import Trustline
from relay.network_graph.graph import CurrencyNetworkGraph, Account
from relay.network_graph.graph_constants import (
    creditline_ab,
    creditline_ba,
    interest_ab,
    interest_ba,
    fees_outstanding_a,
    fees_outstanding_b,
    m_time,
    balance_ab,
)
from relay.network_graph.interests import calculate_interests

addresses = ['0x0A', '0x0B', '0x0C', '0x0D', '0x0E']
A, B, C, D, E = addresses
F = '0x0F'
G = '0x10'
H = '0x11'


SECONDS_PER_YEAR = 60*60*24*365


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
    return {A: [Trustline(B, 200, 200, interest_ba=1000)]}


@pytest.fixture
def basic_data():
    data = {creditline_ab: 0,
            creditline_ba: 0,
            interest_ab: 0,
            interest_ba: 0,
            fees_outstanding_a: 0,
            fees_outstanding_b: 0,
            m_time: 0,
            balance_ab: 0}

    return data


@pytest.fixture()
def basic_account(basic_data):
    return Account(basic_data, A, B)


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


def test_interests_calculation_zero_interest_rate():
    assert calculate_interests(balance=1000, internal_interest_rate=0, delta_time_in_seconds=SECONDS_PER_YEAR) == 0


def test_interests_calculation_returns_integer():
    assert isinstance(calculate_interests(balance=1000,
                                          internal_interest_rate=100,
                                          delta_time_in_seconds=SECONDS_PER_YEAR), int)


def test_interests_calculation_low_interest_rate():
    assert calculate_interests(balance=1000, internal_interest_rate=100, delta_time_in_seconds=SECONDS_PER_YEAR) == 10


def test_interests_calculation_high_interest_rate():
    assert calculate_interests(balance=1000000000000000000, internal_interest_rate=2000,
                               delta_time_in_seconds=SECONDS_PER_YEAR) == pytest.approx(
        1000000000000000000 * (math.exp(0.20) - 1),
        rel=0.01)


def test_interests_calculation_gives_same_result_as_smart_contracts():
    assert calculate_interests(balance=1000000000000000000,
                               internal_interest_rate=2000,
                               delta_time_in_seconds=SECONDS_PER_YEAR
                               ) == 221402758160169828  # taken from contract calculation


def tests_interests_calculation_no_time():
    assert calculate_interests(balance=1000, internal_interest_rate=100, delta_time_in_seconds=0) == 0


def test_interests_calculation_negative_balance():
    assert calculate_interests(balance=-1000,
                               internal_interest_rate=100,
                               delta_time_in_seconds=SECONDS_PER_YEAR) == -10


def test_interests_calculation_from_A_balance_positive_relevant_interests(basic_account):
    basic_account.balance = 100  # B owes to A
    basic_account.interest_rate = 100  # interest given by A to B
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == 101


def test_interests_calculation_from_A_balance_negative_relevant_interests(basic_account):
    basic_account.balance = -100  # A owes to B
    basic_account.reverse_interest_rate = 100  # interest given by B to A
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == -101


def test_interests_calculation_from_A_balance_positive_irrelevant_interests(basic_account):
    basic_account.balance = 100  # B owes to A
    basic_account.reverse_interest_rate = 100  # interest given by B to A
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == 100


def test_interests_calculation_from_A_balance_negative_irrelevant_interests(basic_account):
    basic_account.balance = -100  # A owes to B
    basic_account.interest_rate = 100  # interest given by A to B
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == -100


def test_interests_calculation_delta_time(basic_account):
    basic_account.balance = 100
    basic_account.m_time = SECONDS_PER_YEAR
    basic_account.interest_rate = 100
    assert basic_account.balance_with_interests(2*SECONDS_PER_YEAR) == 101


def test_interests_path_from_A_balance_positive_relevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=100, m_time=1505260800, interest_ab=100)]}
    # B owes to A
    # 1% interest given by A to B
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(A, B, 100)
    assert path == [A, B]


def test_interests_path_from_A_balance_negative_relevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=-100, m_time=1505260800, interest_ba=100)]}
    # A owes to B
    # 1% interest given by B to A
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(A, B, 100)
    assert path == []


def test_interests_path_from_A_balance_positive_irrelevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=100, m_time=1505260800, interest_ba=100)]}
    # B owes to A
    # 1% interest given by B to A
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(A, B, 100)
    assert path == [A, B]


def test_interests_path_from_A_balance_negative_irrelevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=-100, m_time=1505260800, interest_ab=100)]}
    # A owes to B
    # 1% interest given by A to B
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(A, B, 100)
    assert path == [A, B]


def test_interests_path_from_B_balance_positive_relevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=100, m_time=1505260800, interest_ab=100)]}
    # B owes to A
    # 1% interest given by A to B
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(B, A, 100)
    assert path == []


def test_interests_path_from_B_balance_negative_relevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=-100, m_time=1505260800, interest_ba=100)]}
    # A owes to B
    # 1% interest given by B to A
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(B, A, 100)
    assert path == [B, A]


def test_interests_path_from_B_balance_positive_irrelevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=100, m_time=1505260800, interest_ba=100)]}
    # B owes to A
    # 1% interest given by B to A
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(B, A, 100)
    assert path == [B, A]


def test_interests_path_from_B_balance_negative_irrelevant_interests(community_with_simple_trustlines):
    dict = {A: [Trustline(B, 200, 200, balance_ab=-100, m_time=1505260800, interest_ab=100)]}
    # A owes to B
    # 1% interest given by A to B
    community = CurrencyNetworkGraph()
    community.gen_network(dict)

    cost, path = community.find_path(B, A, 100)
    assert path == [B, A]
