import math
from collections import namedtuple
from typing import List

from relay.blockchain.currency_network_events import (
    BalanceUpdateEvent,
    BalanceUpdateEventType,
    TrustlineUpdateEventType,
)
from relay.network_graph.interests import calculate_interests

InterestAccrued = namedtuple("InterestAccrued", ["value", "interest_rate", "timestamp"])

DIRECTION_SENT = "sent"
DIRECTION_RECEIVED = "received"


def get_list_of_paid_interests_for_trustline(
    events_proxy, currency_network_address, user, counterparty
) -> List[InterestAccrued]:
    """Get all balance changes of a trustline because of interests and the time at which it occurred.
    Assumes the trustline exists"""

    balance_update_events = events_proxy.get_trustline_events(
        currency_network_address, user, counterparty, event_name=BalanceUpdateEventType
    )

    timestamps = [
        balance_update_event.timestamp for balance_update_event in balance_update_events
    ]

    balances = get_sorted_balances_from_update_events(balance_update_events)
    interest_rates = [
        get_interests_rates_of_trustline_for_user_before_timestamp(
            events_proxy,
            currency_network_address,
            user,
            counterparty,
            balance,
            timestamp,
        )
        for (balance, timestamp) in zip(balances[:-1], timestamps[1:])
    ]

    return [
        InterestAccrued(
            calculate_interests(balance, interest_rates, post_time - pre_time),
            interest_rates,
            post_time,
        )
        for (balance, interest_rates, pre_time, post_time) in zip(
            balances[:-1], interest_rates, timestamps[:-1], timestamps[1:]
        )
    ]


def get_sorted_balances_from_update_events(
    balance_update_events: List[BalanceUpdateEvent]
):
    """Get all balances of a trustline in sorted order from the view of user"""

    def balance_viewed_from_user(balance_update_event):
        if balance_update_event.direction == DIRECTION_SENT:
            return balance_update_event.value
        elif balance_update_event.direction == DIRECTION_RECEIVED:
            return -balance_update_event.value
        else:
            RuntimeError("Unexpected balance update event")

    return [balance_viewed_from_user(event) for event in balance_update_events]


def get_interests_rates_of_trustline_for_user_before_timestamp(
    events_proxy, currency_network_address, user, counterparty, balance, timestamp
):
    """Get the interest rate that would be used to apply interests at a certain timestamp"""
    trustline_update_events = events_proxy.get_trustline_events(
        currency_network_address,
        user,
        counterparty,
        event_name=TrustlineUpdateEventType,
    )

    most_recent_event_before_timestamp = None
    for event in sorted_events(trustline_update_events, reversed=True):
        if event.timestamp < timestamp:
            most_recent_event_before_timestamp = event
            break
    if most_recent_event_before_timestamp is None:
        RuntimeError("No trustline update event found before given timestamp")

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
        RuntimeError("Unexpected trustline update event")


def sorted_events(events, reversed=False):
    def key(event):
        if event.blocknumber is None:
            return math.inf
        return event.blocknumber

    return sorted(events, key=key, reverse=reversed)


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
