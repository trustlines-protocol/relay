import time
from enum import Enum, auto

import psycopg2
import pytest

from relay.blockchain import currency_network_events
from relay.ethindex_db import ethindex_db
from relay.ethindex_db.events_informations import (
    EventsInformationFetcher,
    IdentifiedNotPartOfTransferException,
)
from relay.network_graph.payment_path import FeePayer


@pytest.fixture()
def ethindex_db_for_currency_network(testnetwork2_address):
    conn = psycopg2.connect(
        cursor_factory=psycopg2.extras.RealDictCursor,
        database="trustlines_test",
        user="trustlines_test",
        password="test123",
    )
    return ethindex_db.CurrencyNetworkEthindexDB(
        conn,
        address=testnetwork2_address,
        standard_event_types=currency_network_events.standard_event_types,
        event_builders=currency_network_events.event_builders,
        from_to_types=currency_network_events.from_to_types,
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
    ethindex_db_for_currency_network,
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

    time.sleep(10)

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[2], accounts[1]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 1000
