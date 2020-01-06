import math

import pytest
from tests.unit.network_graph.conftest import addresses

from relay.blockchain.currency_network_proxy import Trustline
from relay.network_graph.graph import Account, NetworkGraphConfig
from relay.network_graph.graph_constants import (
    balance_ab,
    creditline_ab,
    creditline_ba,
    interest_ab,
    interest_ba,
    m_time,
)
from relay.network_graph.interests import (
    DELTA_TIME_MINIMAL_ALLOWED_VALUE,
    calculate_interests,
)

A, B, C, D, E, F, G, H = addresses


SECONDS_PER_YEAR = 60 * 60 * 24 * 365


@pytest.fixture(params=[0, -1, DELTA_TIME_MINIMAL_ALLOWED_VALUE])
def small_non_positive_delta_time(request):
    return request.param


@pytest.fixture
def basic_data():
    data = {
        creditline_ab: 0,
        creditline_ba: 0,
        interest_ab: 0,
        interest_ba: 0,
        m_time: 0,
        balance_ab: 0,
    }

    return data


@pytest.fixture()
def basic_account(basic_data):
    return Account(basic_data, A, B)


def test_interests_calculation_zero_interest_rate():
    assert (
        calculate_interests(
            balance=1000,
            internal_interest_rate=0,
            delta_time_in_seconds=SECONDS_PER_YEAR,
        )
        == 0
    )


def test_interests_calculation_returns_integer():
    assert isinstance(
        calculate_interests(
            balance=1000,
            internal_interest_rate=100,
            delta_time_in_seconds=SECONDS_PER_YEAR,
        ),
        int,
    )


def test_interests_calculation_low_interest_rate():
    assert (
        calculate_interests(
            balance=1000,
            internal_interest_rate=100,
            delta_time_in_seconds=SECONDS_PER_YEAR,
        )
        == 10
    )


def test_interests_calculation_high_interest_rate():
    assert calculate_interests(
        balance=1000000000000000000,
        internal_interest_rate=2000,
        delta_time_in_seconds=SECONDS_PER_YEAR,
    ) == pytest.approx(1000000000000000000 * (math.exp(0.20) - 1), rel=0.01)


def test_interests_calculation_gives_same_result_as_smart_contracts():
    assert (
        calculate_interests(
            balance=1000000000000000000,
            internal_interest_rate=2000,
            delta_time_in_seconds=SECONDS_PER_YEAR,
        )
        == 221402758160169828
    )  # taken from contract calculation


def tests_interests_calculation_no_time():
    assert (
        calculate_interests(
            balance=1000, internal_interest_rate=100, delta_time_in_seconds=0
        )
        == 0
    )


def test_interests_calculation_negative_balance():
    assert (
        calculate_interests(
            balance=-1000,
            internal_interest_rate=100,
            delta_time_in_seconds=SECONDS_PER_YEAR,
        )
        == -10
    )


def test_interests_calculation_from_A_balance_positive_relevant_interests(
    basic_account
):
    basic_account.balance = 100  # B owes to A
    basic_account.interest_rate = 100  # interest given by A to B
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == 101


def test_interests_calculation_from_A_balance_negative_relevant_interests(
    basic_account
):
    basic_account.balance = -100  # A owes to B
    basic_account.reverse_interest_rate = 100  # interest given by B to A
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == -101


def test_interests_calculation_from_A_balance_positive_irrelevant_interests(
    basic_account
):
    basic_account.balance = 100  # B owes to A
    basic_account.reverse_interest_rate = 100  # interest given by B to A
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == 100


def test_interests_calculation_from_A_balance_negative_irrelevant_interests(
    basic_account
):
    basic_account.balance = -100  # A owes to B
    basic_account.interest_rate = 100  # interest given by A to B
    assert basic_account.balance_with_interests(SECONDS_PER_YEAR) == -100


def test_interests_calculation_delta_time(basic_account):
    basic_account.balance = 100
    basic_account.m_time = SECONDS_PER_YEAR
    basic_account.interest_rate = 100
    assert basic_account.balance_with_interests(2 * SECONDS_PER_YEAR) == 101


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=100, m_time=0, interest_rate_given=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_A_balance_positive_relevant_interests(
    configurable_community
):
    # B owes to A
    # 1% interest given by A to B
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        A, B, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == [A, B]


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=-100, m_time=0, interest_rate_received=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_A_balance_negative_relevant_interests(
    configurable_community
):
    # A owes to B
    # 1% interest given by B to A
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        A, B, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == []


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=100, m_time=0, interest_rate_received=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_A_balance_positive_irrelevant_interests(
    configurable_community
):
    # B owes to A
    # 1% interest given by B to A
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        A, B, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == [A, B]


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=-100, m_time=0, interest_rate_given=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_A_balance_negative_irrelevant_interests(
    configurable_community
):
    # A owes to B
    # 1% interest given by A to B
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        A, B, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == [A, B]


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=100, m_time=0, interest_rate_given=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_B_balance_positive_relevant_interests(
    configurable_community
):
    # B owes to A
    # 1% interest given by A to B
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        B, A, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == []


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=-100, m_time=0, interest_rate_received=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_B_balance_negative_relevant_interests(
    configurable_community
):
    # A owes to B
    # 1% interest given by B to A
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        B, A, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == [B, A]


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=100, m_time=0, interest_rate_received=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_B_balance_positive_irrelevant_interests(
    configurable_community
):
    # B owes to A
    # 1% interest given by B to A
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        B, A, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == [B, A]


@pytest.mark.parametrize(
    "configurable_community",
    [
        NetworkGraphConfig(
            trustlines=[
                Trustline(
                    A, B, 200, 200, balance=-100, m_time=0, interest_rate_given=100
                )
            ]
        )
    ],
    indirect=["configurable_community"],
)
def test_interests_path_from_B_balance_negative_irrelevant_interests(
    configurable_community
):
    # A owes to B
    # 1% interest given by A to B
    cost, path = configurable_community.find_transfer_path_sender_pays_fees(
        B, A, 100, timestamp=SECONDS_PER_YEAR
    )
    assert path == [B, A]


def test_calculate_interests_time_glitch(small_non_positive_delta_time):
    calculate_interests(
        balance=1000000000,
        internal_interest_rate=1000,
        delta_time_in_seconds=small_non_positive_delta_time,
    ) == 0


def test_calculate_interests_delta_time_out_of_bounds():
    with pytest.raises(ValueError):
        calculate_interests(
            balance=1000000000,
            internal_interest_rate=1000,
            delta_time_in_seconds=DELTA_TIME_MINIMAL_ALLOWED_VALUE - 1,
        )
