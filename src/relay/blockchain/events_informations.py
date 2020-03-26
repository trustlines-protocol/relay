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
from relay.network_graph.payment_path import FeePayer

logger = logging.getLogger("event_info")

DIRECTION_SENT = "sent"
DIRECTION_RECEIVED = "received"


@attr.s
class InterestAccrued:
    value = attr.ib()
    interest_rate = attr.ib()
    timestamp = attr.ib()


@attr.s
class TransferInformation:
    currency_network = attr.ib()
    path = attr.ib()
    value = attr.ib()
    fee_payer = attr.ib()
    total_fees = attr.ib()
    fees_paid = attr.ib()


class EventsInformationFetcher:
    def __init__(self, events_proxy):
        self.events_proxy = events_proxy

    def get_list_of_paid_interests_for_trustline(
        self, currency_network_address, user, counterparty
    ) -> List[InterestAccrued]:
        """Get all balance changes of a trustline because of interests and the time at which it occurred."""

        balance_update_events = self.events_proxy.get_trustline_events(
            currency_network_address,
            user,
            counterparty,
            event_name=BalanceUpdateEventType,
        )
        trustline_update_events = self.events_proxy.get_trustline_events(
            currency_network_address,
            user,
            counterparty,
            event_name=TrustlineUpdateEventType,
        )

        return get_accrued_interests_from_events(
            balance_update_events, trustline_update_events
        )

    def get_list_of_paid_interests_for_trustline_in_between_timestamps(
        self, currency_network_address, user, counterparty, start_time, end_time
    ):
        all_accrued_interests = self.get_list_of_paid_interests_for_trustline(
            currency_network_address, user, counterparty
        )
        return filter_list_of_accrued_interests_for_time_window(
            all_accrued_interests, start_time, end_time
        )

    def get_transfer_details(self, tx_hash):

        all_events_of_tx = self.events_proxy.get_transaction_events(tx_hash)
        transfer_events_in_tx = filter_events(all_events_of_tx, TransferEventType)
        if len(transfer_events_in_tx) == 0:
            raise TransferNotFoundException(tx_hash)
        if len(transfer_events_in_tx) > 1:
            raise MultipleTransferFoundException(tx_hash)
        transfer_event = transfer_events_in_tx[0]

        currency_network_address = transfer_event.network_address

        sorted_balance_updates = get_balance_update_events_for_transfer(
            all_events_of_tx, transfer_event
        )
        delta_balances_along_path = self.get_delta_balances_of_transfer(
            currency_network_address, sorted_balance_updates
        )

        transfer_path = get_transfer_path(sorted_balance_updates)

        fees_paid = delta_balances_along_path[1:-1]
        value_sent = -delta_balances_along_path[0]
        value_received = delta_balances_along_path[-1]
        transfer_value = transfer_event.value

        if transfer_value == value_sent:
            fee_payer = FeePayer.RECEIVER
        elif transfer_value == value_received:
            fee_payer = FeePayer.SENDER
        else:
            raise RuntimeError("Transfer value differs from value sent and received.")

        total_fees = value_sent - value_received

        return TransferInformation(
            currency_network=currency_network_address,
            path=transfer_path,
            value=transfer_value,
            fee_payer=fee_payer,
            total_fees=total_fees,
            fees_paid=fees_paid,
        )

    def get_delta_balances_of_transfer(
        self, currency_network_address, sorted_balance_updates
    ):
        """Returns the balance changes along the path because of a given transfer"""
        post_balances = []
        for balance_update in sorted_balance_updates:
            post_balances.append(balance_update.value)

        pre_balances = []
        for balance_update in sorted_balance_updates:
            from_ = balance_update.from_
            to = balance_update.to
            pre_balance = self.get_previous_balance(
                currency_network_address, from_, to, balance_update
            )
            pre_balances.append(pre_balance)

        interests = []
        for balance_update in sorted_balance_updates:
            interest = self.get_interest_at(currency_network_address, balance_update)
            interests.append(interest)

        # sender balance change
        delta_balances = [post_balances[0] - pre_balances[0] - interests[0]]

        # mediator balance changes
        for i in range(len(sorted_balance_updates) - 1):
            next_tl_balance_change = (
                post_balances[i + 1] - pre_balances[i + 1] - interests[i + 1]
            )
            previous_tl_balance_change = (
                post_balances[i] - pre_balances[i] - interests[i]
            )
            delta_balances.append(next_tl_balance_change - previous_tl_balance_change)

        # receiver balance change
        delta_balances.append(-(post_balances[-1] - pre_balances[-1] - interests[-1]))

        return delta_balances

    def get_previous_balance(
        self, currency_network_address, a, b, balance_update_event
    ):
        """Returns the balance before a given balance update event"""
        balance_update_events = self.get_all_balance_update_events_for_trustline(
            currency_network_address, a, b
        )

        # find the corresponding event
        for i, event in enumerate(balance_update_events):
            if event_id(balance_update_event) == event_id(event):
                index = i
                break
        else:
            raise RuntimeError("Could not find balance update")
        index -= 1

        if index < 0:
            return 0

        return get_balance_from_update_event_viewed_from_a(
            balance_update_events[index], a
        )

    def get_all_balance_update_events_for_trustline(
        self, currency_network_address, a, b
    ):
        """Get all balance update events of a trustline in sorted order"""
        return self.events_proxy.get_trustline_events(
            event_name=BalanceUpdateEventType,
            user_address=a,
            counterparty_address=b,
            contract_address=currency_network_address,
        )

    def get_interest_at(self, currency_network_address, balance_update_event):
        """Returns the applied interests at a given balance update"""
        from_ = balance_update_event.from_
        to = balance_update_event.to
        timestamp = balance_update_event.timestamp

        # TODO: this is not optimal, we fetch information we already got
        accrued_interests = self.get_list_of_paid_interests_for_trustline(
            currency_network_address, from_, to
        )

        for accrued_interest in accrued_interests:
            if accrued_interest.timestamp == timestamp:
                return accrued_interest.value
        return 0


def balance_viewed_from_user(balance_update_event):
    if balance_update_event.direction == DIRECTION_SENT:
        return balance_update_event.value
    elif balance_update_event.direction == DIRECTION_RECEIVED:
        return -balance_update_event.value
    else:
        raise RuntimeError("Unexpected balance update event")


def sorted_events(events, reverse=False):
    def log_index_key(event):
        if event.log_index is None:
            raise RuntimeError("No log index, events cannot be ordered truthfully.")
        return event.log_index

    def block_number_key(event):
        if event.blocknumber is None:
            return math.inf
        return event.blocknumber

    return sorted(
        events, key=lambda event: (block_number_key(event), log_index_key(event))
    )


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


def filter_list_of_accrued_interests_for_time_window(
    accrued_interests: List[InterestAccrued], start_time, end_time
):
    filtered_list = []
    for interest in accrued_interests:
        if interest.timestamp <= end_time and interest.timestamp >= start_time:
            filtered_list.append(interest)
    return filtered_list


def filter_events(all_events, event_type):
    return [event for event in all_events if event.type == event_type]


def get_transfer_path(sorted_balance_updates):
    """Returns the transfer path of the given transfer without the sender"""
    path_from_events = []
    path_from_events.append(sorted_balance_updates[0].from_)
    path_from_events.extend(
        [balance_update.to for balance_update in sorted_balance_updates]
    )

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


def get_balance_from_update_event_viewed_from_a(balance_update_event, a):
    if balance_update_event.from_ == a:
        return balance_update_event.value
    elif balance_update_event.to == a:
        return -balance_update_event.value
    else:
        RuntimeError("Unexpected balance update event")


def event_id(event):
    return event.transaction_id, event.log_index


class TransferNotFoundException(Exception):
    def __init__(self, tx_hash):
        self.tx_hash = tx_hash


class MultipleTransferFoundException(Exception):
    def __init__(self, tx_hash):
        self.tx_hash = tx_hash
