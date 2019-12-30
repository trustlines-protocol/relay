import time

import pytest
from tests.unit.network_graph.conftest import addresses

from relay.blockchain.currency_network_proxy import Trustline
from relay.network_graph.graph import (
    CurrencyNetworkGraphForTesting as CurrencyNetworkGraph,
)
from relay.network_graph.payment_path import FeePayer, PaymentPath

A, B, C, D, E, F, G, H = addresses


def assert_maximum_path(community, max_path, max_amount):
    """Asserts that the found path and amount is indeed the maximum"""
    fee, path = community.find_transfer_path_sender_pays_fees(
        max_path[0], max_path[-1], max_amount
    )
    assert path == max_path
    fee, path = community.find_transfer_path_sender_pays_fees(
        max_path[0], max_path[-1], max_amount + 1
    )
    assert path == []


@pytest.fixture
def complextrustlines():
    return [
        Trustline(A, B, 50000, 50000),
        Trustline(A, C, 50000, 50000),
        Trustline(B, D, 50000, 50000),
        Trustline(C, D, 50000, 50000),
        Trustline(D, E, 50000, 50000),
        Trustline(E, F, 50000, 50000),
        Trustline(F, G, 50000, 50000),
        Trustline(G, H, 50000, 50000),
    ]


@pytest.fixture
def balance_trustlines():
    return [Trustline(A, B, 20, 30, balance=10), Trustline(B, C, 200, 250, balance=-20)]


@pytest.fixture
def balances_community(balance_trustlines):
    community = CurrencyNetworkGraph()
    community.gen_network(balance_trustlines)
    return community


@pytest.fixture
def complex_community_with_trustlines_and_fees(complextrustlines):
    community = CurrencyNetworkGraph(capacity_imbalance_fee_divisor=100)
    community.gen_network(complextrustlines)
    return community


@pytest.fixture
def complex_community_with_trustlines_and_fees_33(complextrustlines):
    community = CurrencyNetworkGraph(capacity_imbalance_fee_divisor=33)
    community.gen_network(complextrustlines)
    return community


@pytest.fixture
def complex_community_with_trustlines_and_fees_202(complextrustlines):
    community = CurrencyNetworkGraph(capacity_imbalance_fee_divisor=202)
    community.gen_network(complextrustlines)
    return community


@pytest.fixture
def complex_community_with_trustlines_and_fees_10(complextrustlines):
    community = CurrencyNetworkGraph(capacity_imbalance_fee_divisor=10)
    community.gen_network(complextrustlines)
    return community


@pytest.fixture
def complex_community_with_trustlines(complextrustlines):
    community = CurrencyNetworkGraph()
    community.gen_network(complextrustlines)
    return community


@pytest.fixture()
def complex_community_with_trustlines_and_fees_configurable_balances(
    complex_community_with_trustlines, request
):
    """A graph where the balances can be configured. Expects a list of tuples of (user, counter_party, balance)"""
    for user, counter_party, balance in request.param:
        complex_community_with_trustlines.update_balance(user, counter_party, balance)
    return complex_community_with_trustlines


@pytest.fixture(
    params=[
        CurrencyNetworkGraph.find_transfer_path_sender_pays_fees,
        CurrencyNetworkGraph.find_transfer_path_receiver_pays_fees,
    ]
)
def parametrised_find_transfer_path_function(community_with_trustlines, request):

    return request.param


def test_users(community_with_trustlines):
    community = community_with_trustlines
    assert len(community.users) == 5  # should have 5 users
    assert (
        len(set(community.users) & set(addresses)) == 5
    )  # all users should be in the graph


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


def test_frozen_account_summary(community_with_trustlines):
    community_with_trustlines.freeze_trustline(D, C)
    account = community_with_trustlines.get_account_sum(D, C)

    assert account.is_frozen is True
    assert account.available == 0


def test_frozen_aggregated_account_summary(community_with_trustlines):
    community_with_trustlines.update_balance(A, E, 10)

    account = community_with_trustlines.get_account_sum(A)
    assert account.balance == 10

    community_with_trustlines.freeze_trustline(A, E)
    account = community_with_trustlines.get_account_sum(A)
    assert account.balance == 0


def test_update_trustline(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B, A).creditline_received == 100
    community.update_trustline(A, B, 200, 500, 5, 2)
    account_sum = community.get_account_sum(B, A)
    assert account_sum.creditline_given == 500
    assert account_sum.creditline_received == 200
    assert account_sum.interest_rate_given == 2
    assert account_sum.interest_rate_received == 5


def test_update_balance(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(B).balance == 0
    community.update_balance(A, B, 20)
    community.update_balance(B, C, 10)
    assert community.get_account_sum(B).balance == -10


def test_close_trustline_no_cost_exact_amount(
    complex_community_with_trustlines_and_fees
):
    """A owes money to B and A wants to reduce that amount with the help of C"""
    complex_community_with_trustlines_and_fees.update_balance(
        A, B, -10000
    )  # amount B owes A
    complex_community_with_trustlines_and_fees.update_balance(A, C, 10000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, -10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 10000)
    now = int(time.time())
    payment_path = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        now, A, B
    )
    assert payment_path == PaymentPath(
        fee=0, path=[A, C, D, B, A], value=10000, fee_payer=FeePayer.SENDER
    )


def test_close_trustline_not_enough_capacity(
    complex_community_with_trustlines_and_fees
):
    """A owes money to B and A wants to reduce that amount with the help of C"""
    complex_community_with_trustlines_and_fees.update_balance(
        A, B, -100000
    )  # amount B owes A
    complex_community_with_trustlines_and_fees.update_balance(A, C, 10000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, -10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 10000)
    now = int(time.time())
    payment_path = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        now, A, B
    )
    assert payment_path == PaymentPath(
        fee=0, path=[], value=100000, fee_payer=FeePayer.SENDER
    )


def test_close_trustline_first_edge_insufficient_capacity(
    complex_community_with_trustlines_and_fees
):
    """A owes money to B and A wants to reduce that amount with the help of C"""
    complex_community_with_trustlines_and_fees.update_balance(
        A, B, -10000
    )  # amount B owes A
    complex_community_with_trustlines_and_fees.update_balance(A, C, -50000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, -10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 10000)
    now = int(time.time())
    payment_path = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        now, A, B
    )
    assert payment_path.path == []


def test_close_trustline_last_edge_insufficient_capacity(
    complex_community_with_trustlines_and_fees
):
    """A owes money to B and A wants to reduce that amount with the help of C"""
    complex_community_with_trustlines_and_fees.update_balance(
        A, B, 50000
    )  # amount B owes A
    complex_community_with_trustlines_and_fees.update_balance(A, C, 10000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, -10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 10000)
    now = int(time.time())
    payment_path = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        now, A, B
    )
    assert payment_path.path == []


@pytest.mark.parametrize(
    "complex_community_with_trustlines_and_fees_configurable_balances, source, destination",
    [
        ([], A, B),
        ([], A, C),
        ([], A, D),
        ([], A, E),
        ([(A, B, 10000)], A, B),
        ([(A, B, 49899), (A, C, -50000)], A, B),
        ([(A, B, -50000 + 12345), (A, C, -50000)], A, B),
        ([(A, B, 10000)], A, B),
        ([(A, C, 10000), (C, D, 10000)], A, D),
    ],
    indirect=["complex_community_with_trustlines_and_fees_configurable_balances"],
)
def test_capacity_is_maximum(
    complex_community_with_trustlines_and_fees_configurable_balances,
    source,
    destination,
):
    """Tests for some testdata that the maximum sendable amount is indeed the maximum """
    sendable, max_path = complex_community_with_trustlines_and_fees_configurable_balances.find_maximum_capacity_path(
        source, destination
    )
    assert_maximum_path(
        complex_community_with_trustlines_and_fees_configurable_balances,
        max_path,
        sendable,
    )


def test_capacity_path_single_hop(complex_community_with_trustlines):
    """test for getting the capacity of the path A-B"""
    source = A
    destination = B

    sendable, max_path = complex_community_with_trustlines.find_maximum_capacity_path(
        source, destination
    )
    assert max_path == [A, B]
    assert sendable == 50000


def test_capacity_path_single_hop_more_capacity(complex_community_with_trustlines):
    """test whether the balance A-B impacts capacity"""
    complex_community_with_trustlines.update_balance(A, B, 10000)
    value, path = complex_community_with_trustlines.find_maximum_capacity_path(A, B)
    assert path == [A, B]
    assert value == 60000


def test_capacity_path_single_hop_less_capacity(complex_community_with_trustlines):
    """test whether the balance A-B impacts capacity"""
    complex_community_with_trustlines.update_balance(A, B, -10000)
    complex_community_with_trustlines.update_balance(A, C, -10000)
    value, path = complex_community_with_trustlines.find_maximum_capacity_path(A, B)
    assert path == [A, B]
    assert value == 40000


def test_capacity_path_multi_hops_negative_balance(complex_community_with_trustlines):
    """Tests multihop, A-C balance has to be updated so path A-B is used"""
    complex_community_with_trustlines.update_balance(A, C, -10000)

    value, path = complex_community_with_trustlines.find_maximum_capacity_path(A, E)

    assert path == [A, B, D, E]
    assert value == 50000


def test_capacity_path_multi_hops_negative_balance_lowers_capacity(
    complex_community_with_trustlines
):
    """Tests whether lowering the balance lowers the capacity"""
    complex_community_with_trustlines.update_balance(A, C, -20000)
    complex_community_with_trustlines.update_balance(A, B, -10000)

    value, path = complex_community_with_trustlines.find_maximum_capacity_path(A, E)

    assert path == [A, B, D, E]
    assert value == 40000


def test_capacity_path_multi_hops_positive_balance(complex_community_with_trustlines):
    """Tests whether increasing the balance increases the capacity"""
    complex_community_with_trustlines.update_balance(A, C, 10000)
    complex_community_with_trustlines.update_balance(C, D, 10000)
    complex_community_with_trustlines.update_balance(D, E, 10000)

    value, path = complex_community_with_trustlines.find_maximum_capacity_path(A, E)

    assert path == [A, C, D, E]
    assert value == 60000


def test_capacity_path_single_hop_with_fees(complex_community_with_trustlines_and_fees):
    """test for getting the capacity of the path A-B"""
    source = A
    destination = B

    sendable, max_path = complex_community_with_trustlines_and_fees.find_maximum_capacity_path(
        source, destination
    )
    assert max_path == [A, B]
    assert sendable == 50000


def test_capacity_path_multi_hop_with_fees(complex_community_with_trustlines_and_fees):
    """test for getting the capacity of the path A-E"""
    source = A
    destination = E

    sendable, max_path = complex_community_with_trustlines_and_fees.find_maximum_capacity_path(
        source, destination
    )
    assert max_path == [A, B, D, E]
    assert sendable == 49005


def test_capacity_path_multi_hop_with_fees_one_hop_no_fee(
    complex_community_with_trustlines_and_fees
):
    """Test for getting the capacity if one of the hops has no fees"""
    complex_community_with_trustlines_and_fees.update_balance(
        B, D, 50000
    )  # Results in no fee for this hop

    source = A
    destination = E

    sendable, max_path = complex_community_with_trustlines_and_fees.find_maximum_capacity_path(
        source, destination
    )
    assert max_path == [A, B, D, E]
    assert sendable == 49500


def test_max_capacity_estimation_no_fees_on_one_path(
    complex_community_with_trustlines_and_fees
):
    """Test that it does not return the wrong path only because the total capacity is bigger but
    it is not accounted for the fees"""
    complex_community_with_trustlines_and_fees.update_trustline(A, B, 50001, 50001)
    complex_community_with_trustlines_and_fees.update_trustline(B, D, 50001, 50001)
    complex_community_with_trustlines_and_fees.update_trustline(A, C, 50000, 0)
    complex_community_with_trustlines_and_fees.update_trustline(C, D, 50000, 0)
    complex_community_with_trustlines_and_fees.update_balance(A, C, 50000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 50000)

    source = A
    destination = D

    sendable, max_path = complex_community_with_trustlines_and_fees.find_maximum_capacity_path(
        source, destination
    )

    assert max_path == [A, C, D]
    assert sendable == 50000
    assert_maximum_path(complex_community_with_trustlines_and_fees, max_path, sendable)


def test_max_capacity_estimation_different_length_paths(
    community_with_trustlines_and_fees
):
    """Test that a longer path is not chosen because the fees along the path make it too expensive"""
    community_with_trustlines_and_fees.update_trustline(A, E, 149, 149)

    source = A
    destination = E

    sendable, max_path = community_with_trustlines_and_fees.find_maximum_capacity_path(
        source, destination
    )
    assert max_path == [A, E]
    assert sendable == 149
    assert_maximum_path(community_with_trustlines_and_fees, max_path, sendable)


def test_capacity_path_single_hop_reducing_imbalance(
    complex_community_with_trustlines_and_fees
):
    """Test whether a path with potential reduction of imbalance will show to provide more capacity and less fees
    this exposes the bug detailed in https://github.com/trustlines-protocol/mobileapp/issues/296"""
    complex_community_with_trustlines_and_fees.update_balance(A, B, 50000)

    source = A
    destination = B

    sendable, max_path = complex_community_with_trustlines_and_fees.find_maximum_capacity_path(
        source, destination
    )

    assert_maximum_path(complex_community_with_trustlines_and_fees, max_path, sendable)


def test_max_capacity_estimation_long_path(
    complex_community_with_trustlines_and_fees_10
):
    """Tests whether the estimation of the capacity still work for a long path with minimal capacity in middle"""
    complex_community_with_trustlines_and_fees_10.update_balance(A, C, -50000)

    complex_community_with_trustlines_and_fees_10.update_balance(A, B, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(B, D, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(D, E, -49899)
    complex_community_with_trustlines_and_fees_10.update_balance(E, F, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(F, G, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(G, H, -49000)

    source = A
    destination = H

    sendable, max_path = complex_community_with_trustlines_and_fees_10.find_maximum_capacity_path(
        source, destination
    )

    assert max_path == [A, B, D, E, F, G, H]
    assert_maximum_path(
        complex_community_with_trustlines_and_fees_10, max_path, sendable
    )


def test_max_capacity_estimation_long_path_offset_by_two(
    complex_community_with_trustlines_and_fees_10
):
    """Tests whether the estimation of the capacity still work for a long path with minimal capacity in middle"""
    complex_community_with_trustlines_and_fees_10.update_balance(A, C, -50000)

    complex_community_with_trustlines_and_fees_10.update_balance(A, B, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(B, D, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(D, E, -49899 + 2)
    complex_community_with_trustlines_and_fees_10.update_balance(E, F, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(F, G, -49000)
    complex_community_with_trustlines_and_fees_10.update_balance(G, H, -49000)

    source = A
    destination = H

    sendable, max_path = complex_community_with_trustlines_and_fees_10.find_maximum_capacity_path(
        source, destination
    )
    assert max_path == [A, B, D, E, F, G, H]

    assert_maximum_path(
        complex_community_with_trustlines_and_fees_10, max_path, sendable
    )


def test_max_path_closed_trustlines(balances_community):
    """
    Tests whether we have an assertion error when we look for max path on a closed trustline with negative balance
    See issue https://github.com/trustlines-protocol/relay/issues/285
    """

    balances_community.update_trustline(B, C, 0, 0)
    value, path = balances_community.find_maximum_capacity_path(B, C)

    assert value == 0
    assert path == []


def test_max_path_ignores_frozen_lines(community_with_trustlines):
    community = community_with_trustlines

    value, path = community.find_maximum_capacity_path(A, D)
    assert path == [A, E, D]

    community.freeze_trustline(A, E)
    value, path = community.find_maximum_capacity_path(A, D)
    assert path == [A, B, C, D]


def test_mediated_transfer(community_with_trustlines):
    community = community_with_trustlines
    community.mediated_transfer(A, C, 50)
    assert community.get_account_sum(A).balance == -50
    assert community.get_account_sum(B).balance == 0
    assert community.get_account_sum(C).balance == 50
    assert community.get_account_sum(A, B).balance == -50
    assert community.get_account_sum(B, C).balance == -50


def test_path(community_with_trustlines, parametrised_find_transfer_path_function):
    find_path = parametrised_find_transfer_path_function
    community = community_with_trustlines

    cost, path = find_path(community, A, B, 10)
    assert path == [A, B]
    assert cost == 0
    cost, path = find_path(community, A, D, 10)
    assert path == [A, E, D]
    assert cost == 0


def test_no_path(community_with_trustlines, parametrised_find_transfer_path_function):
    community = community_with_trustlines
    find_path = parametrised_find_transfer_path_function

    community.update_trustline(F, G, 100, 0)
    cost, path = find_path(community, G, F, 10)
    assert path == [G, F]
    cost, path = find_path(community, A, G, 10)  # no path at all
    assert path == []


def test_no_capacity(
    community_with_trustlines, parametrised_find_transfer_path_function
):
    community = community_with_trustlines
    find_path = parametrised_find_transfer_path_function

    cost, path = find_path(community, A, E, 550)
    assert path == [A, E]
    cost, path = find_path(community, A, E, 551)
    assert path == []
    cost, path = find_path(community, E, A, 500)
    assert path == [E, A]
    cost, path = find_path(community, E, A, 501)
    assert path == []


def test_no_direction(
    community_with_trustlines, parametrised_find_transfer_path_function
):
    community = community_with_trustlines
    find_path = parametrised_find_transfer_path_function

    community.update_trustline(F, G, 100, 0)
    cost, path = find_path(community_with_trustlines, G, F, 10)
    assert path == [G, F]
    cost, path = find_path(
        community_with_trustlines, F, G, 10
    )  # no creditline in this direction
    assert path == []


def test_valid_path_raises_no_value_error(complex_community_with_trustlines_and_fees):
    """Verifies that the condition for raising a ValueError is not faulty
    see https://github.com/trustlines-protocol/relay/issues/91"""
    complex_community_with_trustlines_and_fees.update_balance(
        A, B, -10000
    )  # amount B owes A because A < B
    complex_community_with_trustlines_and_fees.update_balance(A, C, 10000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, -10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, 10000)
    complex_community_with_trustlines_and_fees.update_balance(D, E, 0)
    # should not raise ValueError
    cost, path = complex_community_with_trustlines_and_fees.find_transfer_path_sender_pays_fees(
        E, A, 10000
    )


def test_max_hops(community_with_trustlines, parametrised_find_transfer_path_function):
    community = community_with_trustlines
    find_path = parametrised_find_transfer_path_function

    cost, path = find_path(community, A, D, 10)
    assert path == [A, E, D]
    cost, path = find_path(community, A, D, 10, max_hops=1)
    assert path == []


def test_finding_path_ignores_frozen_lines(
    community_with_trustlines, parametrised_find_transfer_path_function
):
    community = community_with_trustlines
    find_path = parametrised_find_transfer_path_function

    cost, path = find_path(community, A, D, 10)
    assert path == [A, E, D]
    community.freeze_trustline(A, E)

    cost, path = find_path(community, A, D, 10)
    assert path == [A, B, C, D]


def test_send_back(community_with_trustlines):
    community = community_with_trustlines

    assert community.get_account_sum(A, B).balance == 0
    assert community.find_transfer_path_sender_pays_fees(B, A, 120)[1] == [
        B,
        C,
        D,
        E,
        A,
    ]
    assert community.find_transfer_path_sender_pays_fees(A, B, 120)[1] == [A, B]
    community.mediated_transfer(A, B, 120)
    assert community.get_account_sum(B, A).balance == 120
    assert community.find_transfer_path_sender_pays_fees(B, A, 120)[1] == [B, A]
    assert community.find_transfer_path_sender_pays_fees(A, B, 120)[1] == [
        A,
        E,
        D,
        C,
        B,
    ]
    community.mediated_transfer(B, A, 120)
    assert community.get_account_sum(A, B).balance == 0


def test_send_more(community_with_trustlines):
    community = community_with_trustlines

    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 150
    assert community.get_account_sum(B, A).creditline_left_received == 100
    assert community.find_transfer_path_sender_pays_fees(A, B, 120)[1] == [A, B]
    assert community.find_transfer_path_sender_pays_fees(B, A, 120)[1] == [
        B,
        C,
        D,
        E,
        A,
    ]
    community.mediated_transfer(A, B, 120)
    assert community.get_account_sum(B, A).balance == 120
    assert community.get_account_sum(B, A).creditline_left_received == 220
    assert community.find_transfer_path_sender_pays_fees(A, B, 200)[1] == [
        A,
        E,
        D,
        C,
        B,
    ]
    assert community.find_transfer_path_sender_pays_fees(B, A, 200)[1] == [B, A]
    community.mediated_transfer(B, A, 200)
    assert community.get_account_sum(A, B).balance == 80


def test_send_more_nopath(community_with_trustlines):
    community = community_with_trustlines
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 150
    assert community.get_account_sum(B, A).creditline_left_received == 100
    assert community.find_transfer_path_sender_pays_fees(A, B, 160)[1] == [
        A,
        E,
        D,
        C,
        B,
    ]
    assert community.find_transfer_path_sender_pays_fees(B, A, 160)[1] == [
        B,
        C,
        D,
        E,
        A,
    ]
    community.mediated_transfer(A, B, 50)
    assert community.get_account_sum(B, A).balance == 50
    assert community.get_account_sum(A, B).creditline_left_received == 100
    assert community.get_account_sum(B, A).creditline_left_received == 150
    assert community.find_transfer_path_sender_pays_fees(A, B, 160)[1] == [
        A,
        E,
        D,
        C,
        B,
    ]
    assert community.find_transfer_path_sender_pays_fees(B, A, 160)[1] == [
        B,
        C,
        D,
        E,
        A,
    ]
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


def test_mediated_transfer_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    community.mediated_transfer(A, C, 50)
    assert community.get_account_sum(A).balance == -50 + -1
    assert community.get_account_sum(B).balance == 0 + 1
    assert community.get_account_sum(C).balance == 50
    assert community.get_account_sum(A, B).balance == -50 + -1
    assert community.get_account_sum(B, C).balance == -50


def test_path_with_fees_sender_pays(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_transfer_path_sender_pays_fees(A, B, 10)
    assert path == [A, B]
    assert cost == 0
    cost, path = community.find_transfer_path_sender_pays_fees(A, D, 10)
    assert path == [A, E, D]
    assert cost == 1


def test_path_with_fees_receiver_pays(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_transfer_path_receiver_pays_fees(A, B, 10)
    assert path == [A, B]
    assert cost == 0
    cost, path = community.find_transfer_path_receiver_pays_fees(A, D, 10)
    assert path == [A, E, D]
    assert cost == 1


def test_path_fee_symmetry_sanity(complex_community_with_trustlines_and_fees):
    community = complex_community_with_trustlines_and_fees

    sender_pays = 50000

    cost, path = community.find_transfer_path_receiver_pays_fees(A, H, sender_pays)
    assert path == [A, B, D, E, F, G, H]
    assert cost == 2453

    receiver_receives = sender_pays - cost
    cost, path = community.find_transfer_path_sender_pays_fees(A, H, receiver_receives)
    assert path == [A, B, D, E, F, G, H]
    assert cost == 2453


def test_max_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_transfer_path_sender_pays_fees(A, D, 110)
    assert path == [A, E, D]
    assert cost == 2
    cost, path = community.find_transfer_path_sender_pays_fees(A, D, 110, max_fees=1)
    assert path == []


def test_no_capacity_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    cost, path = community.find_transfer_path_sender_pays_fees(A, E, 550)
    assert path == [A, E]
    cost, path = community.find_transfer_path_sender_pays_fees(A, E, 551)
    assert path == []
    cost, path = community.find_transfer_path_sender_pays_fees(E, A, 500)
    assert path == [E, A]
    cost, path = community.find_transfer_path_sender_pays_fees(E, A, 501)
    assert path == []


def test_send_back_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    assert community.get_account_sum(A, B).balance == 0
    assert community.find_transfer_path_sender_pays_fees(B, A, 120)[1] == [
        B,
        C,
        D,
        E,
        A,
    ]
    assert community.find_transfer_path_sender_pays_fees(A, B, 120)[1] == [A, B]
    assert community.mediated_transfer(A, B, 120) == 0
    assert community.get_account_sum(B, A).balance == 120
    assert community.find_transfer_path_sender_pays_fees(B, A, 120)[1] == [B, A]
    assert community.find_transfer_path_sender_pays_fees(A, B, 120)[1] == [
        A,
        E,
        D,
        C,
        B,
    ]
    assert community.mediated_transfer(B, A, 120) == 0
    assert community.get_account_sum(A, B).balance == 0


def test_send_more_with_fees(community_with_trustlines_and_fees):
    community = community_with_trustlines_and_fees
    assert community.get_account_sum(A, B).balance == 0
    assert community.get_account_sum(A, B).creditline_left_received == 150
    assert community.get_account_sum(B, A).creditline_left_received == 100
    assert community.find_transfer_path_sender_pays_fees(A, B, 120)[1] == [A, B]
    assert community.find_transfer_path_sender_pays_fees(B, A, 120)[1] == [
        B,
        C,
        D,
        E,
        A,
    ]
    assert community.mediated_transfer(A, B, 120) == 0
    assert community.get_account_sum(B, A).balance == 120 + 0
    assert community.get_account_sum(B, A).creditline_left_received == 220 + 0
    assert community.find_transfer_path_sender_pays_fees(A, B, 201)[1] == []
    assert community.find_transfer_path_sender_pays_fees(B, A, 200)[1] == [B, A]
    assert community.mediated_transfer(B, A, 200) == 0
    assert community.get_account_sum(A, B).balance == 80


def test_close_trustline_zero_balance(complex_community_with_trustlines_and_fees):
    """H owes money to C and C wants to close the trustline"""
    result = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        timestamp=int(time.time()), source=C, target=H
    )
    assert result == PaymentPath(fee=0, path=[], value=0, fee_payer=FeePayer.SENDER)


def test_close_trustline_positive_balance(complex_community_with_trustlines_and_fees):
    """H owes money to C and C wants to close the trustline"""
    complex_community_with_trustlines_and_fees.update_balance(C, H, 5000)
    result = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        timestamp=int(time.time()), source=C, target=H
    )
    assert result == PaymentPath(
        fee=198, path=[C, H, G, F, E, D, C], value=5000, fee_payer=FeePayer.RECEIVER
    )


def test_close_trustline_negative_balance(complex_community_with_trustlines_and_fees):
    """C owes money to H and C wants to close the trustline"""
    complex_community_with_trustlines_and_fees.update_balance(C, H, -5000)
    result = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        timestamp=int(time.time()), source=C, target=H
    )
    assert result == PaymentPath(
        fee=261, path=[C, D, E, F, G, H, C], value=5000, fee_payer=FeePayer.SENDER
    )


def test_close_trustline_with_cost_exact_amount(
    complex_community_with_trustlines_and_fees
):
    """A owes money to B and A wants to close the trustline"""
    complex_community_with_trustlines_and_fees.update_balance(
        A, B, -10000
    )  # amount B owes A
    complex_community_with_trustlines_and_fees.update_balance(A, C, -10000)
    complex_community_with_trustlines_and_fees.update_balance(B, D, 10000)
    complex_community_with_trustlines_and_fees.update_balance(C, D, -10000)
    result = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        timestamp=int(time.time()), source=A, target=B
    )
    assert result == PaymentPath(
        fee=309, path=[A, C, D, B, A], value=10000, fee_payer=FeePayer.SENDER
    )


def test_close_trustline_multi(complex_community_with_trustlines_and_fees):
    """A owes money to H and A wants to close the trustline"""
    complex_community_with_trustlines_and_fees.update_balance(A, H, -5000)
    result = complex_community_with_trustlines_and_fees.close_trustline_path_triangulation(
        timestamp=int(time.time()), source=A, target=H
    )
    assert result in [
        PaymentPath(
            fee=315,
            path=[A, B, D, E, F, G, H, A],
            value=5000,
            fee_payer=FeePayer.SENDER,
        ),
        PaymentPath(
            fee=315,
            path=[A, C, D, E, F, G, H, A],
            value=5000,
            fee_payer=FeePayer.SENDER,
        ),
    ]


def test_update_to_closed_trustlines_remove_from_graph(
    complex_community_with_trustlines_and_fees
):
    """Tests that an edge / node is removed from the graph
    when a trustline is estimated as closed after updating the credit limits"""
    assert complex_community_with_trustlines_and_fees.graph.has_edge(G, H)
    complex_community_with_trustlines_and_fees.update_trustline(G, H, 0, 0)
    assert complex_community_with_trustlines_and_fees.graph.has_edge(G, H) is False
    assert complex_community_with_trustlines_and_fees.graph.has_node(G)
    assert complex_community_with_trustlines_and_fees.graph.has_node(H) is False


def test_update_balance_to_closed_trustlines_remove_from_graph(
    complex_community_with_trustlines_and_fees
):
    """Tests that an edge / node is removed from the graph
    when a trustline is estimated as closed after updating the balance"""
    # we update the balance first so that it is not removed when updating the credit limit
    complex_community_with_trustlines_and_fees.update_balance(G, H, 10)
    complex_community_with_trustlines_and_fees.update_trustline(G, H, 0, 0)

    assert complex_community_with_trustlines_and_fees.graph.has_edge(G, H)
    complex_community_with_trustlines_and_fees.update_balance(G, H, 0)
    assert complex_community_with_trustlines_and_fees.graph.has_edge(G, H) is False
    assert complex_community_with_trustlines_and_fees.graph.has_node(G)
    assert complex_community_with_trustlines_and_fees.graph.has_node(H) is False
