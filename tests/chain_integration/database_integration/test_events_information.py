import functools
import time
from enum import Enum, auto

import pytest
from tests.chain_integration.conftest import CurrencyNetworkProxy

from relay.blockchain import currency_network_events
from relay.ethindex_db import ethindex_db
from relay.ethindex_db.events_informations import (
    EventsInformationFetcher,
    IdentifiedNotPartOfTransferException,
)
from relay.network_graph.graph import CurrencyNetworkGraph
from relay.network_graph.payment_path import FeePayer


"""
The tests are running a postgres database and ethindex to tests out getting and processing event information.
They assume that you can run docker and docker-compose.
Otherwise, you can run the tests with `--local-db` option and have a local postgres environment with:
- user: POSTGRES_USER
- password: POSTGRES_PASSWORD
- database: POSTGRES_DATABASE
- accessible on localhost:postgres_port
See tests/chain_integration/database_integration/conftest.py for actual values
"""


@pytest.fixture()
def ethindex_db_for_currency_network(currency_network, generic_db_connection):
    return make_ethindex_db(currency_network.address, generic_db_connection)


@pytest.fixture()
def ethindex_db_for_currency_network_with_trustlines(
    currency_network_with_trustlines_session, generic_db_connection
):
    return make_ethindex_db(
        currency_network_with_trustlines_session.address, generic_db_connection
    )


@pytest.fixture()
def ethindex_db_for_currency_network_with_trustlines_and_interests(
    currency_network_with_trustlines_and_interests_session, generic_db_connection
):
    return make_ethindex_db(
        currency_network_with_trustlines_and_interests_session.address,
        generic_db_connection,
    )


def make_ethindex_db(network_address, conn):
    return ethindex_db.CurrencyNetworkEthindexDB(
        conn,
        address=network_address,
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
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    years,
    interests,
    wait_for_ethindex_to_sync,
):
    """Test with a transfer A -> B the interests viewed from B"""
    currency_network = currency_network_with_trustlines_and_interests_session
    path = [accounts[0], accounts[1], accounts[2], accounts[3]]
    accrue_interests(currency_network, web3, chain, path, years)
    wait_for_ethindex_to_sync()

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[2], accounts[1]
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
def test_get_interests_received_for_trustline_negative_balance(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    years,
    interests,
    wait_for_ethindex_to_sync,
):
    """Test with a transfer B -> A the interests viewed from A"""
    currency_network = currency_network_with_trustlines_and_interests_session
    path = [accounts[3], accounts[2], accounts[1], accounts[0]]
    accrue_interests(currency_network, web3, chain, path, years)
    wait_for_ethindex_to_sync()

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[1], accounts[2]
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
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    years,
    interests,
    wait_for_ethindex_to_sync,
):
    """Test the with a transfer A -> B the interests viewed from A"""
    currency_network = currency_network_with_trustlines_and_interests_session
    path = [accounts[0], accounts[1], accounts[2], accounts[3]]
    accrue_interests(currency_network, web3, chain, path, years)
    wait_for_ethindex_to_sync()

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[1], accounts[2]
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
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    years,
    interests,
    wait_for_ethindex_to_sync,
):
    """Test with a transfer B -> A the interests viewed from B"""
    currency_network = currency_network_with_trustlines_and_interests_session
    path = [accounts[3], accounts[2], accounts[1], accounts[0]]
    accrue_interests(currency_network, web3, chain, path, years)
    wait_for_ethindex_to_sync()

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[2], accounts[1]
    )

    list_of_interests = [
        accrued_interest.value for accrued_interest in accrued_interests
    ]
    assert list_of_interests == interests
    for accrued_interest in accrued_interests:
        assert accrued_interest.interest_rate == 2000


class LookupMethod(Enum):
    TX_HASH = auto()
    TRANSFER_ID = auto()
    BALANCE_UPDATE_ID = auto()


@pytest.mark.parametrize("lookup_method", list(LookupMethod))
@pytest.mark.parametrize("fee_payer", ["sender", "receiver"])
@pytest.mark.parametrize("path", [[0, 1], [0, 1, 2, 3], [3, 2, 1, 0]])
def test_get_transfer_information_path(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session,
    web3,
    accounts,
    path,
    fee_payer,
    lookup_method,
    wait_for_ethindex_to_sync,
):
    """
    test that we can get the path of a sent transfer from the transfer event
    """
    network = currency_network_with_trustlines_session
    account_path = [accounts[i] for i in path]
    value = 100
    block_number = web3.eth.blockNumber

    if fee_payer == "sender":
        tx_hash = network.transfer_on_path(value, account_path).hex()
    elif fee_payer == "receiver":
        tx_hash = network.transfer_receiver_pays_on_path(value, account_path).hex()
    else:
        assert False, "Invalid fee payer"
    wait_for_ethindex_to_sync()

    if (
        lookup_method == LookupMethod.TRANSFER_ID
        or lookup_method == LookupMethod.BALANCE_UPDATE_ID
    ):
        if lookup_method == LookupMethod.TRANSFER_ID:
            event = network._proxy.events.Transfer().getLogs(fromBlock=block_number)[0]
        elif lookup_method == LookupMethod.BALANCE_UPDATE_ID:
            event = network._proxy.events.BalanceUpdate().getLogs(
                fromBlock=block_number
            )[0]
        else:
            assert False, "Unexpected lookup method"
        transfer_information = EventsInformationFetcher(
            ethindex_db_for_currency_network_with_trustlines
        ).get_transfer_details_for_id(event["blockHash"].hex(), event["logIndex"])[0]
    elif lookup_method == LookupMethod.TX_HASH:
        transfer_information = EventsInformationFetcher(
            ethindex_db_for_currency_network_with_trustlines
        ).get_transfer_details_for_tx(tx_hash)[0]
    else:
        assert False, "Unknown lookup method"

    assert transfer_information.path == account_path


@pytest.mark.parametrize("lookup_method", list(LookupMethod))
@pytest.mark.parametrize("fee_payer", [FeePayer.SENDER, FeePayer.RECEIVER])
def test_get_transfer_information_values(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session,
    web3,
    accounts,
    fee_payer,
    lookup_method,
    wait_for_ethindex_to_sync,
):
    """
    test that we can get the path of a sent transfer from the transfer event
    """
    network = currency_network_with_trustlines_session
    path = [accounts[i] for i in [0, 1, 2, 3, 4, 5, 6]]
    number_of_mediators = len(path) - 2
    value = 10
    block_number = web3.eth.blockNumber

    if fee_payer == FeePayer.SENDER:
        tx_hash = network.transfer_on_path(value, path).hex()
    elif fee_payer == FeePayer.RECEIVER:
        tx_hash = network.transfer_receiver_pays_on_path(value, path).hex()
    else:
        assert False, "Invalid fee payer"
    wait_for_ethindex_to_sync()

    if (
        lookup_method == LookupMethod.TRANSFER_ID
        or lookup_method == LookupMethod.BALANCE_UPDATE_ID
    ):
        if lookup_method == LookupMethod.TRANSFER_ID:
            event = network._proxy.events.Transfer().getLogs(fromBlock=block_number)[0]
        elif lookup_method == LookupMethod.BALANCE_UPDATE_ID:
            event = network._proxy.events.BalanceUpdate().getLogs(
                fromBlock=block_number
            )[0]
        else:
            assert False, "Unexpected lookup method"
        transfer_information = EventsInformationFetcher(
            ethindex_db_for_currency_network_with_trustlines
        ).get_transfer_details_for_id(event["blockHash"].hex(), event["logIndex"])[0]
    elif lookup_method == LookupMethod.TX_HASH:
        transfer_information = EventsInformationFetcher(
            ethindex_db_for_currency_network_with_trustlines
        ).get_transfer_details_for_tx(tx_hash)[0]
    else:
        assert False, "Unknown lookup method"

    assert transfer_information.fees_paid == [1, 1, 1, 1, 1]
    assert transfer_information.value == value
    assert transfer_information.total_fees == number_of_mediators
    assert transfer_information.fee_payer == fee_payer
    assert transfer_information.currency_network == network.address


def test_transfer_by_wrong_balance_update(
    ethindex_db_for_currency_network,
    currency_network,
    web3,
    accounts,
    chain,
    wait_for_ethindex_to_sync,
):
    A, B, *rest = accounts

    currency_network.update_trustline_with_accept(A, B, 1000, 1000, 100, 100)
    currency_network.transfer_on_path(100, [A, B])
    now = int(time.time())
    chain.time_travel(now + 3600 * 24 * 365)
    # Should emit BalanceUpdate
    currency_network.update_trustline_with_accept(A, B, 2000, 2000, 200, 200)

    block_number = web3.eth.blockNumber
    events = currency_network._proxy.events.BalanceUpdate().getLogs(
        fromBlock=block_number
    )
    assert len(events) == 1

    event = events[0]

    wait_for_ethindex_to_sync()

    with pytest.raises(IdentifiedNotPartOfTransferException):
        EventsInformationFetcher(
            ethindex_db_for_currency_network
        ).get_transfer_details_for_id(event["blockHash"].hex(), event["logIndex"])


def assert_fee(fee, value, from_, to, tx_hash, timestamp):
    assert fee.value == value
    assert fee.from_ == from_
    assert fee.to == to
    assert fee.transaction_hash == tx_hash
    assert fee.timestamp == timestamp


def make_transfer(currency_network, value, path, fee_payer):
    if fee_payer == "sender":
        tx_hash = currency_network.transfer_on_path(value, path)
    else:
        tx_hash = currency_network.transfer_receiver_pays_on_path(value, path)
    return tx_hash


@pytest.mark.parametrize("fee_payer", ["sender", "receiver"])
@pytest.mark.parametrize("transfer_value, fee_value", [(150, 2), (1150, 12)])
def test_get_mediation_fees(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    accounts,
    fee_payer,
    transfer_value,
    fee_value,
    wait_for_ethindex_to_sync,
):
    currency_network = currency_network_with_trustlines_and_interests_session
    tx_hash = make_transfer(
        currency_network,
        transfer_value,
        [accounts[0], accounts[1], accounts[2]],
        fee_payer,
    )
    timestamp = web3.eth.getBlock("latest")["timestamp"]

    wait_for_ethindex_to_sync()
    graph = CurrencyNetworkGraph(
        capacity_imbalance_fee_divisor=currency_network.capacity_imbalance_fee_divisor,
        default_interest_rate=currency_network.default_interest_rate,
        custom_interests=currency_network.custom_interests,
        prevent_mediator_interests=currency_network.prevent_mediator_interests,
    )
    fees = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_earned_mediation_fees(accounts[1], graph)

    assert len(fees) == 1
    assert_fee(
        fees[0],
        value=fee_value,
        from_=accounts[0],
        to=accounts[2],
        tx_hash=tx_hash,
        timestamp=timestamp,
    )


@pytest.mark.parametrize("fee_payer", ["sender", "receiver"])
@pytest.mark.parametrize("transfer_value, fee_value", [(150, 2), (1150, 12)])
def test_get_mediation_fees_with_pollution(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session: CurrencyNetworkProxy,
    web3,
    accounts,
    fee_payer,
    transfer_value,
    fee_value,
    wait_for_ethindex_to_sync,
):
    """test getting the mediation fees while there are other trustline updates / transfer polluting events"""
    currency_network = currency_network_with_trustlines_and_interests_session
    custom_make_transfer = functools.partial(
        make_transfer,
        currency_network,
        transfer_value,
        [accounts[0], accounts[1], accounts[2]],
        fee_payer,
    )

    tx_hash0 = custom_make_transfer()
    timestamp0 = web3.eth.getBlock("latest")["timestamp"]

    currency_network.update_trustline_and_reject(
        accounts[0], accounts[1], 100_000, 100_000
    )
    tx_hash1 = custom_make_transfer()
    timestamp1 = web3.eth.getBlock("latest")["timestamp"]

    currency_network.update_trustline_with_accept(
        accounts[0], accounts[1], 10_000, 10_000
    )
    tx_hash2 = custom_make_transfer()
    timestamp2 = web3.eth.getBlock("latest")["timestamp"]

    currency_network.transfer_on_path(123, [accounts[1], accounts[0]])
    currency_network.transfer_receiver_pays_on_path(
        123, [accounts[1], accounts[2], accounts[3]]
    )

    tx_hash3 = custom_make_transfer()
    timestamp3 = web3.eth.getBlock("latest")["timestamp"]

    wait_for_ethindex_to_sync()
    graph = CurrencyNetworkGraph(
        capacity_imbalance_fee_divisor=currency_network.capacity_imbalance_fee_divisor,
        default_interest_rate=currency_network.default_interest_rate,
        custom_interests=currency_network.custom_interests,
        prevent_mediator_interests=currency_network.prevent_mediator_interests,
    )
    fees = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_earned_mediation_fees(accounts[1], graph)

    assert len(fees) == 4
    custom_assert_fee = functools.partial(
        assert_fee, value=fee_value, from_=accounts[0], to=accounts[2]
    )
    custom_assert_fee(fee=fees[0], tx_hash=tx_hash0, timestamp=timestamp0)
    custom_assert_fee(fee=fees[1], tx_hash=tx_hash1, timestamp=timestamp1)
    custom_assert_fee(fee=fees[2], tx_hash=tx_hash2, timestamp=timestamp2)
    custom_assert_fee(fee=fees[3], tx_hash=tx_hash3, timestamp=timestamp3)
