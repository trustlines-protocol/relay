import pytest

from relay.blockchain.events_informations import (
    get_list_of_paid_interests_for_trustline,
)


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [0, 2]), ([1, 4, 2, 3], [1, 9, 8, 19])]
)
def test_get_interests_for_trustline(
    currency_network_with_trustlines, web3, chain, accounts, years, interests
):
    """Sending 10 with a time difference of x years where the interest rate is 10%
    """
    currency_network = currency_network_with_trustlines
    currency_network.transfer(accounts[1], 10, 1000, [accounts[1], accounts[2]])

    path = [accounts[0], accounts[1], accounts[2], accounts[3]]

    for year in years:
        timestamp = web3.eth.getBlock("latest").timestamp
        timestamp += (3600 * 24 * 365) * year + 1

        chain.time_travel(timestamp)
        chain.mine_block()
        currency_network.transfer(accounts[0], 9, 1000, path, b"")

    list_of_interests = [
        interests_timestamps[0]
        for interests_timestamps in get_list_of_paid_interests_for_trustline(
            currency_network, currency_network, accounts[2], accounts[1]
        )
    ]

    assert list_of_interests == interests
