import pytest

from relay.blockchain.events_informations import (
    get_list_of_paid_interests_for_trustline,
)


def accrue_interests(currency_network, web3, chain, path, years):
    """Sending 10 with a time difference of x years, path should be something like
    [account[0], sender, receiver, account[3]]"""
    currency_network.transfer(path[0], 9, 1000, path)

    for year in years:
        timestamp = web3.eth.getBlock("latest").timestamp
        timestamp += (3600 * 24 * 365) * year + 1

        chain.time_travel(timestamp)
        chain.mine_block()
        currency_network.transfer(path[0], 9, 1000, path, b"")


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [0, 2]), ([1, 4, 2, 3], [1, 9, 8, 19])]
)
def test_get_interests_received_for_trustline_positive_balance(
    currency_network_with_trustlines_and_interests,
    web3,
    chain,
    accounts,
    years,
    interests,
):
    """Test with a transfer A -> B the interests viewed from B"""
    currency_network = currency_network_with_trustlines_and_interests
    path = [accounts[0], accounts[1], accounts[2], accounts[3]]
    accrue_interests(currency_network, web3, chain, path, years)

    accrued_interests = get_list_of_paid_interests_for_trustline(
        currency_network, currency_network, accounts[2], accounts[1]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 1000


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [0, 4]), ([1, 4, 2, 3], [2, 24, 26, 74])]
)
def test_get_interests_received_for_trustline_negaive_balance(
    currency_network_with_trustlines_and_interests,
    web3,
    chain,
    accounts,
    years,
    interests,
):
    """Test with a transfer B -> A the interests viewed from A"""
    currency_network = currency_network_with_trustlines_and_interests
    path = [accounts[3], accounts[2], accounts[1], accounts[0]]
    accrue_interests(currency_network, web3, chain, path, years)

    accrued_interests = get_list_of_paid_interests_for_trustline(
        currency_network, currency_network, accounts[1], accounts[2]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 2000


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [0, -2]), ([1, 4, 2, 3], [-1, -9, -8, -19])]
)
def test_get_interests_paid_for_trustline_positive_balance(
    currency_network_with_trustlines_and_interests,
    web3,
    chain,
    accounts,
    years,
    interests,
):
    """Test the with a transfer A -> B the interests viewed from A"""
    currency_network = currency_network_with_trustlines_and_interests
    path = [accounts[0], accounts[1], accounts[2], accounts[3]]
    accrue_interests(currency_network, web3, chain, path, years)

    accrued_interests = get_list_of_paid_interests_for_trustline(
        currency_network, currency_network, accounts[1], accounts[2]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 1000


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [0, -4]), ([1, 4, 2, 3], [-2, -24, -26, -74])]
)
def test_get_interests_paid_for_trustline_negative_balance(
    currency_network_with_trustlines_and_interests,
    web3,
    chain,
    accounts,
    years,
    interests,
):
    """Test with a transfer B -> A the interests viewed from B"""
    currency_network = currency_network_with_trustlines_and_interests
    path = [accounts[3], accounts[2], accounts[1], accounts[0]]
    accrue_interests(currency_network, web3, chain, path, years)

    accrued_interests = get_list_of_paid_interests_for_trustline(
        currency_network, currency_network, accounts[2], accounts[1]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 2000
