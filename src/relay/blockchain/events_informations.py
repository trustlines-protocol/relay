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


@attr.s
class FeesPaid:
    sender = attr.ib()
    receiver = attr.ib()
    value = attr.ib()


@attr.s
class TransferInformation:
    path = attr.ib()
    fees_paid = attr.ib()
    value_sent = attr.ib()
    value_received = attr.ib()
    total_fees = attr.ib()


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

        return self.get_accrued_interests_from_events(
            balance_update_events, trustline_update_events
        )

    def get_accrued_interests_from_events(
        self, balance_update_events, trustline_update_events
    ):
        accrued_interests = []
        for (pre_balance_event, post_balance_event) in toolz.itertoolz.sliding_window(
            2, balance_update_events
        ):
            balance = self.balance_viewed_from_user(pre_balance_event)
            interest_rate = self.get_interests_rates_of_trustline_for_user_before_timestamp(
                trustline_update_events, balance, post_balance_event.timestamp
            )
            interest_value = calculate_interests(
                balance,
                interest_rate,
                post_balance_event.timestamp - pre_balance_event.timestamp,
            )
            accrued_interests.append(
                InterestAccrued(
                    interest_value, interest_rate, post_balance_event.timestamp
                )
            )

        return accrued_interests

    def balance_viewed_from_user(self, balance_update_event):
        if balance_update_event.direction == DIRECTION_SENT:
            return balance_update_event.value
        elif balance_update_event.direction == DIRECTION_RECEIVED:
            return -balance_update_event.value
        else:
            raise RuntimeError("Unexpected balance update event")

    def get_interests_rates_of_trustline_for_user_before_timestamp(
        self, trustline_update_events, balance, timestamp
    ):
        """Get the interest rate that would be used to apply interests at a certain timestamp"""

        most_recent_event_before_timestamp = None
        for event in self.sorted_events(trustline_update_events, reverse=True):
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

    def sorted_events(self, events, reverse=False):
        def key(event):
            if event.blocknumber is None:
                return math.inf
            return event.blocknumber

        return sorted(events, key=key, reverse=reverse)

    def get_list_of_paid_interests_for_trustline_in_between_timestamps(
        self, currency_network_address, user, counterparty, start_time, end_time
    ):
        all_accrued_interests = self.get_list_of_paid_interests_for_trustline(
            currency_network_address, user, counterparty
        )
        return self.filter_list_of_accrued_interests_for_time_window(
            all_accrued_interests, start_time, end_time
        )

    def filter_list_of_accrued_interests_for_time_window(
        self, accrued_interests: List[InterestAccrued], start_time, end_time
    ):
        filtered_list = []
        for interest in accrued_interests:
            if interest.timestamp <= end_time and interest.timestamp >= start_time:
                filtered_list.append(interest)
        return filtered_list

    def get_transfer_details(self, tx_hash):

        all_events_of_tx = self.events_proxy.get_all_transaction_events(tx_hash)
        transfer_events_in_tx = self.get_all_transfer_events(all_events_of_tx)
        if len(transfer_events_in_tx) == 0:
            raise TransferNotFoundException(tx_hash)
        if len(transfer_events_in_tx) > 1:
            raise MultipleTransferFoundException(tx_hash)
        transfer_event = transfer_events_in_tx[0]

        currency_network_address = transfer_event.network_address

        sorted_balance_updates = self.get_balance_update_events_for_transfer(
            all_events_of_tx, transfer_event
        )
        delta_balances_along_path = self.get_delta_balances_of_transfer(
            currency_network_address, sorted_balance_updates
        )

        transfer_path = self.get_transfer_path(sorted_balance_updates)

        fees_paid = self.get_paid_fees_along_path(
            transfer_path, delta_balances_along_path
        )
        value_sent = -delta_balances_along_path[0]
        value_received = delta_balances_along_path[len(delta_balances_along_path) - 1]
        total_fees = value_sent - value_received

        return TransferInformation(
            path=transfer_path,
            fees_paid=fees_paid,
            value_sent=value_sent,
            value_received=value_received,
            total_fees=total_fees,
        )

    def get_all_transfer_events(self, all_events):
        transfer_events = []
        for event in all_events:
            if event.type == TransferEventType:
                transfer_events.append(event)
        return transfer_events

    def get_transfer_path(self, sorted_balance_updates):
        """Returns the transfer path of the given transfer without the sender"""
        path_from_events = []
        path_from_events.append(sorted_balance_updates[0].from_)
        for event in sorted_balance_updates:
            path_from_events.append(event.to)

        return path_from_events

    def get_balance_update_events_for_transfer(self, all_events, transfer_event):
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

    def get_paid_fees_along_path(self, transfer_path, delta_balances):
        fees_values = delta_balances[1:-1]
        fees_paid = []
        for sender, receiver in zip(transfer_path[:-2], transfer_path[1:-1]):
            fees_paid.append(FeesPaid(sender, receiver, fees_values[len(fees_paid)]))
        return fees_paid

    def get_delta_balances_of_transfer(
        self, currency_network_address, sorted_balance_updates
    ):
        """Returns the balance changes along the path because of a given transfer"""
        post_balances = []
        for event in sorted_balance_updates:
            post_balances.append(event.value)

        pre_balances = []
        for event in sorted_balance_updates:
            from_ = event.from_
            to = event.to
            pre_balance = self.get_previous_balance(
                currency_network_address, from_, to, event
            )
            pre_balances.append(pre_balance)

        interests = []
        for event in sorted_balance_updates:
            interest = self.get_interest_at(currency_network_address, event)
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
            if self.event_id(balance_update_event) == self.event_id(event):
                index = i
                break
        else:
            raise RuntimeError("Could not find balance update")
        index -= 1

        if index < 0:
            return 0

        return self.get_balance_from_update_event_viewed_from_a(
            balance_update_events[index], a
        )

    def get_balance_from_update_event_viewed_from_a(self, balance_update_event, a):
        if balance_update_event.from_ == a:
            return balance_update_event.value
        elif balance_update_event.to == a:
            return -balance_update_event.value
        else:
            RuntimeError("Unexpected balance update event")

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

    def event_id(self, event):
        return event.transaction_id, event.log_index  # , event["blockHash"]

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


class TransferNotFoundException(Exception):
    def __init__(self, tx_hash):
        self.tx_hash = tx_hash


class MultipleTransferFoundException(Exception):
    def __init__(self, tx_hash):
        self.tx_hash = tx_hash
