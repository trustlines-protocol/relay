from typing import List

from relay.blockchain.currency_network_events import (
    BalanceUpdateEvent,
    BalanceUpdateEventType,
)
from relay.network_graph.interests import calculate_interests

DIRECTION_SENT = "sent"
DIRECTION_RECEIVED = "received"


def get_list_of_paid_interests_for_trustline(
    events_proxy, currency_network_address, user, counterparty
):
    """Get all balance changes of a trustline because of interests and the time at which it occurred"""
    # TODO: find the interests rates instead of hard coding
    interest_rate = 1000

    balance_update_events = events_proxy.get_trustline_events(
        currency_network_address, user, counterparty, event_name=BalanceUpdateEventType
    )
    print(balance_update_events)

    timestamps = [
        balance_update_event.timestamp for balance_update_event in balance_update_events
    ]

    balances = get_sorted_balances_from_update_events(balance_update_events)

    return [
        (calculate_interests(balance, interest_rate, post_time - pre_time), post_time)
        for (balance, pre_time, post_time) in zip(
            balances[:-1], timestamps[:-1], timestamps[1:]
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
