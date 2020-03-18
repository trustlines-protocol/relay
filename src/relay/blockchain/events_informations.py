import logging
import math
from typing import List

import attr
import toolz

from relay.blockchain.currency_network_events import (
    BalanceUpdateEventType,
    TransferEventType,
    TrustlineUpdateEventType,
)
from relay.network_graph.interests import calculate_interests

logger = logging.getLogger("event_info")

DIRECTION_SENT = "sent"
DIRECTION_RECEIVED = "received"


@attr.s
class InterestAccrued:
    value = attr.ib()
    interest_rate = attr.ib()
    timestamp = attr.ib()


def get_list_of_paid_interests_for_trustline(
    events_proxy, currency_network_address, user, counterparty
) -> List[InterestAccrued]:
    """Get all balance changes of a trustline because of interests and the time at which it occurred."""

    balance_update_events = events_proxy.get_trustline_events(
        currency_network_address, user, counterparty, event_name=BalanceUpdateEventType
    )
    trustline_update_events = events_proxy.get_trustline_events(
        currency_network_address,
        user,
        counterparty,
        event_name=TrustlineUpdateEventType,
    )

    return get_accrued_interests_from_events(
        balance_update_events, trustline_update_events
    )


def get_accrued_interests_from_events(balance_update_events, trustline_update_events):
    accrued_interests = []
    for (pre_balance_event, post_balance_event) in toolz.itertoolz.sliding_window(
        2, balance_update_events
    ):
        balance = balance_viewed_from_user(pre_balance_event)
        interest_rate = get_interests_rates_of_trustline_for_user_before_timestamp(
            trustline_update_events, balance, post_balance_event.timestamp
        )
        interest_value = calculate_interests(
            balance,
            interest_rate,
            post_balance_event.timestamp - pre_balance_event.timestamp,
        )
        accrued_interests.append(
            InterestAccrued(interest_value, interest_rate, post_balance_event.timestamp)
        )

    return accrued_interests


def balance_viewed_from_user(balance_update_event):
    if balance_update_event.direction == DIRECTION_SENT:
        return balance_update_event.value
    elif balance_update_event.direction == DIRECTION_RECEIVED:
        return -balance_update_event.value
    else:
        raise RuntimeError("Unexpected balance update event")


def get_interests_rates_of_trustline_for_user_before_timestamp(
    trustline_update_events, balance, timestamp
):
    """Get the interest rate that would be used to apply interests at a certain timestamp"""

    most_recent_event_before_timestamp = None
    for event in sorted_events(trustline_update_events, reverse=True):
        if event.timestamp < timestamp:
            most_recent_event_before_timestamp = event
            break
    if most_recent_event_before_timestamp is None:
        raise RuntimeError("No trustline update event found before given timestamp")

    if most_recent_event_before_timestamp.direction == DIRECTION_SENT:
        if balance >= 0:
            return most_recent_event_before_timestamp.interest_rate_given
        else:
            return most_recent_event_before_timestamp.interest_rate_received
    elif most_recent_event_before_timestamp.direction == DIRECTION_RECEIVED:
        if balance >= 0:
            return most_recent_event_before_timestamp.interest_rate_received
        else:
            return most_recent_event_before_timestamp.interest_rate_given
    else:
        raise RuntimeError("Unexpected trustline update event")


def sorted_events(events, reverse=False):
    def key(event):
        if event.blocknumber is None:
            return math.inf
        return event.blocknumber

    return sorted(events, key=key, reverse=reverse)


def get_list_of_paid_interests_for_trustline_in_between_timestamps(
    events_proxy, currency_network_address, user, counterparty, start_time, end_time
):
    all_accrued_interests = get_list_of_paid_interests_for_trustline(
        events_proxy, currency_network_address, user, counterparty
    )
    return filter_list_of_accrued_interests_for_time_window(
        all_accrued_interests, start_time, end_time
    )


def filter_list_of_accrued_interests_for_time_window(
    accrued_interests: List[InterestAccrued], start_time, end_time
):
    filtered_list = []
    for interest in accrued_interests:
        if interest.timestamp <= end_time and interest.timestamp >= start_time:
            filtered_list.append(interest)
    return filtered_list


def get_tranfer_details(events_proxy, tx_hash):

    all_events = events_proxy.get_all_transaction_events(tx_hash)
    logger.info("all_events")
    logger.info(all_events)
    transfer_events = get_all_transfer_events(all_events)
    if len(transfer_events) == 0:
        raise TransferNotFoundException(tx_hash)
    if len(transfer_events) > 1:
        raise MultipleTransferFoundException(tx_hash)
    transfer_event = transfer_events[0]

    transfer_path = get_transfer_path(all_events, transfer_event)
    logger.info("transfer_path")
    logger.info(transfer_path)
    return transfer_path


def get_all_transfer_events(all_events):
    transfer_events = []
    for event in all_events:
        if event.type == TransferEventType:
            transfer_events.append(event)
    return transfer_events


def get_transfer_path(all_events, transfer_event):
    """Returns the transfer path of the given transfer without the sender"""
    path_from_events = []
    transfer_events = get_balance_update_events_for_transfer(all_events, transfer_event)
    path_from_events.append(transfer_events[0].from_)
    for event in transfer_events:
        path_from_events.append(event.to)

    return path_from_events


def get_balance_update_events_for_transfer(all_events, transfer_event):
    """Returns all balance update events in the correct order that belongs to the transfer event"""
    log_index = transfer_event.log_index
    sender = transfer_event.from_
    receiver = transfer_event.to

    balance_events = []
    saw_sender_event = False
    saw_receiver_event = False

    # Search backwards for releated BalanceUpdate events
    for i in range(log_index - 1, -1, -1):
        for event in all_events:
            if event.log_index == i:
                assert (
                    event.type == BalanceUpdateEventType
                ), "Wrong event type for events before transfer event"
                balance_events.append(event)
                if event.to == receiver:
                    saw_receiver_event = True
                if event.from_ == sender:
                    saw_sender_event = True
                break
        if saw_sender_event and saw_receiver_event:
            break
    else:
        assert False, "Could not find all BalanceUpdate events"

    if balance_events[0].from_ != sender:
        # For the sender pays case, they are reverse
        balance_events.reverse()

    assert balance_events[0].from_ == sender
    assert balance_events[-1].to == receiver
    return balance_events


class TransferNotFoundException(Exception):
    def __init__(self, tx_hash):
        self.tx_hash = tx_hash


class MultipleTransferFoundException(Exception):
    def __init__(self, tx_hash):
        self.tx_hash = tx_hash
