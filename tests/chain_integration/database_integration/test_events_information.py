import functools
import time
from enum import Enum, auto

import pytest
from tests.chain_integration.conftest import CurrencyNetworkProxy

from relay.ethindex_db.events_informations import (
    EventsInformationFetcher,
    IdentifiedNotPartOfTransferException,
)
from relay.network_graph.graph import CurrencyNetworkGraph
from relay.network_graph.interests import calculate_interests
from relay.network_graph.payment_path import FeePayer

ONE_YEAR_IN_SECONDS = 365 * 3600 * 24


def accrue_interests(currency_network, web3, chain, path, years):
    """Sending 10 with a time difference of x years, path should be something like
    [account[0], sender, receiver, account[3]]"""
    currency_network.transfer(path[0], 9, 1000, path)

    for year in years:
        timestamp = web3.eth.getBlock("latest").timestamp
        timestamp += ONE_YEAR_IN_SECONDS * year + 1

        chain.time_travel(timestamp)
        chain.mine_block()
        currency_network.transfer(path[0], 9, 1000, path, b"")


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [2]), ([1, 4, 2, 3], [1, 9, 8, 19])]
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
    "years, interests", [([0, 1], [4]), ([1, 4, 2, 3], [2, 24, 26, 74])]
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
    "years, interests", [([0, 1], [-2]), ([1, 4, 2, 3], [-1, -9, -8, -19])]
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
    "years, interests", [([0, 1], [-4]), ([1, 4, 2, 3], [-2, -24, -26, -74])]
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


@pytest.mark.parametrize(
    "years, interests", [([0, 1], [2]), ([1, 4, 2, 3], [1, 9, 8, 19])]
)
def test_get_interests_received_open_trustline_with_transfer(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    years,
    interests,
    wait_for_ethindex_to_sync,
):
    """Test that opening a trustline with balance will still allow us to get interests"""
    currency_network = currency_network_with_trustlines_and_interests_session

    currency_network.close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[1], accounts[2], 12345, 12345, 0, 0, False, 123
    )
    currency_network.transfer(accounts[2], 123, 0, [accounts[2], accounts[1]])

    currency_network.update_trustline_with_accept(
        accounts[1], accounts[2], 12345, 12345, 2000, 1000, False, 0
    )

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
    "years, interests", [([0, 1], [4]), ([1, 4, 2, 3], [2, 24, 26, 74])]
)
def test_get_interests_paid_open_trustline_with_transfer(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    years,
    interests,
    wait_for_ethindex_to_sync,
):
    """Test that opening a trustline with balance will still allow us to get paid interests"""
    currency_network = currency_network_with_trustlines_and_interests_session

    currency_network.close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[1], accounts[2], 12345, 12345, 0, 0, False, 123
    )
    currency_network.transfer(accounts[2], 123, 0, [accounts[2], accounts[1]])

    currency_network.update_trustline_with_accept(
        accounts[1], accounts[2], 12345, 12345, 2000, 1000, False, 0
    )

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


def test_get_interests_received_during_opening_of_trustline(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    wait_for_ethindex_to_sync,
):
    """Test that opening a trustline with balance and interests will allow us to get resulting accrued interests"""
    currency_network = currency_network_with_trustlines_and_interests_session
    initial_transfer = 100
    interest_rate = 1000

    currency_network.close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[1],
        accounts[2],
        12345,
        12345,
        2000,
        interest_rate,
        False,
        initial_transfer,
    )

    path = [accounts[0], accounts[1], accounts[2], accounts[3]]
    timestamp = web3.eth.getBlock("latest").timestamp
    timestamp += ONE_YEAR_IN_SECONDS + 1
    chain.time_travel(timestamp)
    currency_network.transfer(path[0], 9, 1000, path, b"")

    wait_for_ethindex_to_sync()

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[2], accounts[1]
    )
    assert len(accrued_interests) == 1
    assert accrued_interests[0].value == calculate_interests(
        initial_transfer, interest_rate, ONE_YEAR_IN_SECONDS
    )
    assert accrued_interests[0].interest_rate == interest_rate
    assert accrued_interests[0].timestamp == web3.eth.getBlock("latest").timestamp


def test_get_interests_paid_during_opening_of_trustline(
    ethindex_db_for_currency_network_with_trustlines_and_interests,
    currency_network_with_trustlines_and_interests_session,
    web3,
    chain,
    accounts,
    wait_for_ethindex_to_sync,
):
    """Test that opening a trustline with balance and interests will allow us to get resulting paid interests"""
    currency_network = currency_network_with_trustlines_and_interests_session
    initial_transfer = -100
    interest_rate = 2000

    currency_network.close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[1],
        accounts[2],
        12345,
        12345,
        interest_rate,
        1000,
        False,
        initial_transfer,
    )

    path = [accounts[0], accounts[1], accounts[2], accounts[3]]
    timestamp = web3.eth.getBlock("latest").timestamp
    timestamp += ONE_YEAR_IN_SECONDS + 1
    chain.time_travel(timestamp)
    currency_network.transfer(path[0], 9, 1000, path, b"")

    wait_for_ethindex_to_sync()

    accrued_interests = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines_and_interests
    ).get_list_of_paid_interests_for_trustline(
        currency_network.address, accounts[2], accounts[1]
    )
    assert len(accrued_interests) == 1
    assert accrued_interests[0].value == calculate_interests(
        initial_transfer, interest_rate, ONE_YEAR_IN_SECONDS
    )
    assert accrued_interests[0].interest_rate == interest_rate
    assert accrued_interests[0].timestamp == web3.eth.getBlock("latest").timestamp


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


@pytest.mark.parametrize("lookup_method", list(LookupMethod))
@pytest.mark.parametrize("transfer_value", [100, -100])
def test_get_transfer_information_trustline_update(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session,
    web3,
    accounts,
    lookup_method,
    transfer_value,
    wait_for_ethindex_to_sync,
):
    """
    test that we can get the transfer information from a transfer applied when opening a trustline
    """
    network = currency_network_with_trustlines_session

    initiator = accounts[1]
    counterparty = accounts[2]

    network.close_trustline(initiator, counterparty)
    block_number = web3.eth.blockNumber
    tx_hash = network.update_trustline_with_accept(
        initiator, counterparty, 12345, 12345, 0, 0, False, transfer_value
    ).hex()

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

    if transfer_value > 0:
        assert transfer_information.path == [initiator, counterparty]
    else:
        assert transfer_information.path == [counterparty, initiator]
    assert transfer_information.fees_paid == []
    assert transfer_information.value == abs(transfer_value)
    assert transfer_information.total_fees == 0
    assert transfer_information.extra_data == b""
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

    # Pollution from opening trustline with a transfer
    open_trustline_transfer_value = 123

    currency_network.settle_and_close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[1],
        accounts[2],
        12345,
        12345,
        0,
        0,
        False,
        open_trustline_transfer_value,
    )

    currency_network.settle_and_close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[1],
        accounts[2],
        12345,
        12345,
        0,
        0,
        False,
        -open_trustline_transfer_value,
    )

    currency_network.settle_and_close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[2],
        accounts[1],
        12345,
        12345,
        0,
        0,
        False,
        open_trustline_transfer_value,
    )

    currency_network.settle_and_close_trustline(accounts[1], accounts[2])
    currency_network.update_trustline_with_accept(
        accounts[2],
        accounts[1],
        12345,
        12345,
        0,
        0,
        False,
        -open_trustline_transfer_value,
    )

    tx_hash4 = custom_make_transfer()
    timestamp4 = web3.eth.getBlock("latest")["timestamp"]

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

    assert len(fees) == 5
    custom_assert_fee = functools.partial(
        assert_fee, value=fee_value, from_=accounts[0], to=accounts[2]
    )
    custom_assert_fee(fee=fees[0], tx_hash=tx_hash0, timestamp=timestamp0)
    custom_assert_fee(fee=fees[1], tx_hash=tx_hash1, timestamp=timestamp1)
    custom_assert_fee(fee=fees[2], tx_hash=tx_hash2, timestamp=timestamp2)
    custom_assert_fee(fee=fees[3], tx_hash=tx_hash3, timestamp=timestamp3)
    custom_assert_fee(fee=fees[4], tx_hash=tx_hash4, timestamp=timestamp4)


def get_debts_of_single_currency_network(
    ethindex_db, creditor, currency_network_address
):
    debts_in_all_currency_network = EventsInformationFetcher(
        ethindex_db
    ).get_debt_lists_in_all_networks(creditor)
    assert len(debts_in_all_currency_network.keys()) == 1
    return debts_in_all_currency_network[currency_network_address]


@pytest.mark.parametrize("creditor_number, debtor_number", [(0, 1), (1, 0)])
def test_get_debts(
    ethindex_db_for_currency_network,
    currency_network,
    accounts,
    creditor_number,
    debtor_number,
    wait_for_ethindex_to_sync,
):
    debtor = accounts[debtor_number]
    creditor = accounts[creditor_number]
    debt_value = 123

    currency_network.increase_debt(debtor, creditor, debt_value)

    wait_for_ethindex_to_sync()

    # Test the point of view of creditor
    debts = get_debts_of_single_currency_network(
        ethindex_db_for_currency_network, creditor, currency_network.address
    )
    assert len(debts) == 1
    assert debts[debtor] == debt_value

    # Test the point of view of debtor
    debts = get_debts_of_single_currency_network(
        ethindex_db_for_currency_network, debtor, currency_network.address
    )
    assert len(debts) == 1
    assert debts[creditor] == -debt_value


def test_get_debts_repaid_debt(
    ethindex_db_for_currency_network,
    currency_network,
    accounts,
    wait_for_ethindex_to_sync,
):
    """
    Test getting the debts after canceling a debt to 0
    """
    creditor = accounts[0]
    debtor = accounts[1]
    debt_value = 123

    currency_network.increase_debt(debtor, creditor, debt_value)
    currency_network.increase_debt(creditor, debtor, debt_value)

    wait_for_ethindex_to_sync()
    debts = EventsInformationFetcher(
        ethindex_db_for_currency_network
    ).get_debt_lists_in_all_networks(creditor)
    assert debts == {}


def test_get_debts_multiple_updates(
    ethindex_db_for_currency_network,
    currency_network,
    accounts,
    wait_for_ethindex_to_sync,
):
    """
    Test getting the debts after updating them multiple times
    """
    creditor = accounts[0]
    debtor = accounts[1]
    debt_value = 123

    currency_network.increase_debt(debtor, creditor, debt_value)
    currency_network.increase_debt(debtor, creditor, debt_value)

    wait_for_ethindex_to_sync()
    debts = get_debts_of_single_currency_network(
        ethindex_db_for_currency_network, creditor, currency_network.address
    )
    assert len(debts.keys()) == 1
    assert debts[debtor] == debt_value * 2


def test_get_debts_multiple_debtors(
    ethindex_db_for_currency_network,
    currency_network,
    accounts,
    wait_for_ethindex_to_sync,
):
    """
    Test getting the debts with multiple different debtors
    """
    creditor = accounts[0]
    debtors = [accounts[x] for x in range(1, 5)]
    debt_values = range(1, 5)

    for index in range(len(debtors)):
        currency_network.increase_debt(debtors[index], creditor, debt_values[index])

    wait_for_ethindex_to_sync()
    debts = get_debts_of_single_currency_network(
        ethindex_db_for_currency_network, creditor, currency_network.address
    )
    assert len(debts.keys()) == len(debtors)

    for index in range(len(debtors)):
        assert debts[debtors[index]] == debt_values[index]


def test_get_total_sum_transferred_single_transfer(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session: CurrencyNetworkProxy,
    accounts,
    wait_for_ethindex_to_sync,
):

    sender = accounts[0]
    receiver = accounts[1]
    value = 123

    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[sender, receiver]
    )

    wait_for_ethindex_to_sync()
    sum = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines
    ).get_total_sum_transferred(sender, receiver)

    assert sum == value


def test_get_total_sum_transferred_multi_transfer(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session: CurrencyNetworkProxy,
    accounts,
    wait_for_ethindex_to_sync,
):

    sender = accounts[0]
    receiver = accounts[1]
    value = 11
    number_transfer = 5

    for x in range(number_transfer):
        currency_network_with_trustlines_session.transfer_on_path(
            value, path=[sender, receiver]
        )

    wait_for_ethindex_to_sync()
    sum = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines
    ).get_total_sum_transferred(sender, receiver)

    assert sum == value * number_transfer


def test_get_total_sum_transferred_time_window(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session: CurrencyNetworkProxy,
    accounts,
    wait_for_ethindex_to_sync,
    chain,
):

    sender = accounts[0]
    receiver = accounts[1]
    value = 11
    start_time = 2_000_000_000
    end_time = 2_100_000_000

    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[sender, receiver]
    )
    chain.time_travel(start_time)
    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[sender, receiver]
    )
    chain.time_travel(end_time + 1)
    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[sender, receiver]
    )

    wait_for_ethindex_to_sync()
    sum = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines
    ).get_total_sum_transferred(sender, receiver, start_time, end_time)

    assert sum == value


def test_get_total_sum_transferred_with_noise(
    ethindex_db_for_currency_network_with_trustlines,
    currency_network_with_trustlines_session: CurrencyNetworkProxy,
    accounts,
    wait_for_ethindex_to_sync,
):

    sender = accounts[1]
    receiver = accounts[3]
    value = 11

    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[accounts[0], accounts[1], accounts[2], accounts[3], accounts[4]]
    )
    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[accounts[0], accounts[1], accounts[2], accounts[3]]
    )
    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[accounts[1], accounts[2], accounts[3], accounts[4]]
    )
    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[receiver, accounts[2], sender]
    )
    currency_network_with_trustlines_session.transfer_on_path(
        value, path=[sender, accounts[2], receiver]
    )

    wait_for_ethindex_to_sync()
    sum = EventsInformationFetcher(
        ethindex_db_for_currency_network_with_trustlines
    ).get_total_sum_transferred(sender, receiver)

    assert sum == value


def test_get_total_sum_transferred_trustline_update(
    ethindex_db_for_currency_network,
    currency_network: CurrencyNetworkProxy,
    accounts,
    wait_for_ethindex_to_sync,
):
    """Test getting the sum transferred for transfer occurring while opening a trustline"""
    sender = accounts[0]
    receiver = accounts[1]
    value = 123

    currency_network.update_trustline_with_accept(
        sender, receiver, 12345, 12345, 0, 0, False, value,
    )
    currency_network.settle_and_close_trustline(sender, receiver)
    currency_network.update_trustline_with_accept(
        sender, receiver, 12345, 12345, 0, 0, False, -value,
    )

    wait_for_ethindex_to_sync()
    sum = EventsInformationFetcher(
        ethindex_db_for_currency_network
    ).get_total_sum_transferred(sender, receiver)

    assert sum == value
