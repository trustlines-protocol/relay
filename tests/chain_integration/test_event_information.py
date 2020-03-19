import pytest

from relay.blockchain.events_informations import EventsInformationFetcher


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

    accrued_interests = EventsInformationFetcher(
        currency_network
    ).get_list_of_paid_interests_for_trustline(
        currency_network, accounts[2], accounts[1]
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

    accrued_interests = EventsInformationFetcher(
        currency_network
    ).get_list_of_paid_interests_for_trustline(
        currency_network, accounts[1], accounts[2]
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

    accrued_interests = EventsInformationFetcher(
        currency_network
    ).get_list_of_paid_interests_for_trustline(
        currency_network, accounts[1], accounts[2]
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

    accrued_interests = EventsInformationFetcher(
        currency_network
    ).get_list_of_paid_interests_for_trustline(
        currency_network, accounts[2], accounts[1]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 2000


@pytest.mark.parametrize(
    "path, fee_payer",
    [
        ([0, 1], "sender"),
        ([0, 1, 2, 3], "sender"),
        ([3, 2, 1, 0], "sender"),
        ([0, 1], "receiver"),
        ([0, 1, 2, 3], "receiver"),
        ([3, 2, 1, 0], "receiver"),
    ],
)
def test_get_transfer_information_path(
    currency_network_with_trustlines, accounts, path, fee_payer
):
    """
    test that we can get the path of a sent transfer from the transfer event
    """
    network = currency_network_with_trustlines
    account_path = [accounts[i] for i in path]
    value = 100

    if fee_payer == "sender":
        tx_hash = network.transfer_on_path(value, account_path)
    elif fee_payer == "receiver":
        tx_hash = network.transfer_receiver_pays_on_path(value, account_path)
    else:
        assert False, "Invalid fee payer"

    transfer_information = EventsInformationFetcher(network).get_transfer_details(
        tx_hash
    )
    assert transfer_information.path == account_path


@pytest.mark.parametrize("fee_payer", ["sender", "receiver"])
def test_get_transfer_information_fees_paid(
    currency_network_with_trustlines, accounts, fee_payer
):
    """
    test that we can get the path of a sent transfer from the transfer event
    """
    network = currency_network_with_trustlines
    path = [accounts[i] for i in [0, 1, 2, 3, 4, 5, 6]]
    value = 10

    if fee_payer == "sender":
        tx_hash = network.transfer_on_path(value, path)
    elif fee_payer == "receiver":
        tx_hash = network.transfer_receiver_pays_on_path(value, path)
    else:
        assert False, "Invalid fee payer"

    transfer_information = EventsInformationFetcher(network).get_transfer_details(
        tx_hash
    )
    fees_paid = transfer_information.fees_paid
    for i in range(len(fees_paid)):
        assert fees_paid[i].sender == path[i]
        assert fees_paid[i].receiver == path[i + 1]
        assert fees_paid[i].value == 1
