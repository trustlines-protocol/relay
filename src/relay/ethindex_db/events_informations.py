import logging
import math
import time
from operator import attrgetter
from typing import Dict, Iterable, List, Optional, Union, cast

import attr
import toolz

from relay.blockchain.currency_network_events import (
    BalanceUpdateEvent,
    BalanceUpdateEventType,
    DebtUpdateEvent,
    DebtUpdateEventType,
    TransferEvent,
    TransferEventType,
    TrustlineUpdateEvent,
    TrustlineUpdateEventType,
)
from relay.blockchain.events import BlockchainEvent
from relay.ethindex_db.ethindex_db import CurrencyNetworkEthindexDB
from relay.network_graph.graph import CurrencyNetworkGraph
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
    extra_data = attr.ib()


@attr.s
class MediationFee:
    value = attr.ib()
    from_ = attr.ib()
    to = attr.ib()
    transaction_hash = attr.ib()
    timestamp = attr.ib()


@attr.s
class Debt:
    debtor = attr.ib(type=str)
    value = attr.ib(type=int)
    claimable_value = attr.ib(type=int)
    claim_path = attr.ib(type=Optional[List[str]], init=False)


@attr.s
class DebtsListInCurrencyNetwork:
    currency_network = attr.ib(type=str)
    debts_list = attr.ib(type=List[Debt])


class EventsInformationFetcher:
    def __init__(self, currency_network_db: CurrencyNetworkEthindexDB):
        self._currency_network_db = currency_network_db

    def get_list_of_paid_interests_for_trustline(
        self, currency_network_address, user, counterparty
    ) -> List[InterestAccrued]:
        """Get all balance changes of a trustline because of interests and the time at which it occurred."""

        balance_update_events = self._currency_network_db.get_trustline_events(
            currency_network_address,
            user,
            counterparty,
            event_types=[BalanceUpdateEventType],
        )
        trustline_update_events = self._currency_network_db.get_trustline_events(
            currency_network_address,
            user,
            counterparty,
            event_types=[TrustlineUpdateEventType],
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
        return filter_list_of_information_for_time_window(
            all_accrued_interests, start_time, end_time
        )

    def get_transfer_details_for_id(self, block_hash: str, log_index: int):
        all_events_of_tx = self._currency_network_db.get_transaction_events_by_event_id(
            block_hash,
            log_index,
            event_types=(TransferEventType, BalanceUpdateEventType),
        )
        events_with_given_log_index = filter_events_with_index(
            all_events_of_tx, log_index
        )
        if len(events_with_given_log_index) == 0:
            raise EventNotFoundException(block_hash=block_hash, log_index=log_index)
        assert (
            len(events_with_given_log_index) == 1
        ), "Multiple events with given log index."

        transfer_event = find_transfer_event(
            all_events_of_tx, events_with_given_log_index[0]
        )

        # TODO check that event_with_given_log_index is part of the found transfer, to ensure we did everything correct

        assert transfer_event.type == TransferEventType

        return [self.get_transfer_details(all_events_of_tx, transfer_event)]

    def get_transfer_details_for_tx(self, tx_hash: str):

        all_events_of_tx = self._currency_network_db.get_transaction_events(
            tx_hash, event_types=(TransferEventType, BalanceUpdateEventType)
        )
        transfer_events_in_tx = filter_events_with_type(
            all_events_of_tx, TransferEventType
        )
        if len(transfer_events_in_tx) == 0:
            raise TransferNotFoundException(tx_hash=tx_hash)

        return [
            self.get_transfer_details(all_events_of_tx, transfer_event)
            for transfer_event in transfer_events_in_tx
        ]

    def get_transfer_details(self, all_events, transfer_event):
        """Use a transfer event and all events emitted in transfer transaction to get transfer details"""

        currency_network_address = transfer_event.network_address

        sorted_balance_updates = get_balance_update_events_for_transfer(
            all_events, transfer_event
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
            extra_data=transfer_event.extra_data,
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
        return self._currency_network_db.get_trustline_events(
            event_types=[BalanceUpdateEventType],
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

    def get_earned_mediation_fees(
        self, user_address: str, graph: CurrencyNetworkGraph
    ) -> List[MediationFee]:
        useful_event_types = [
            BalanceUpdateEventType,
            TransferEventType,
            TrustlineUpdateEventType,
        ]
        all_events = self._currency_network_db.get_all_network_events(
            user_address=user_address, event_types=useful_event_types
        )
        all_events = sorted_events(all_events)

        # This event is a standalone balance update that could be:
        # - the first event of a couple of balance updates for a mediated transfer
        # - the first event of a transfer initiated by the user
        # - the last event of a transfer directed to the user
        # - due to an application of interests from a trustline update
        last_standalone_balance_update: Optional[BalanceUpdateEvent] = None
        fees_earned: List[MediationFee] = []

        for event in all_events:
            if event.type == TrustlineUpdateEventType:
                event = cast(TrustlineUpdateEvent, event)
                if does_trustline_update_trigger_balance_update(graph, event):
                    # The last standalone balance update is not due to mediation, but to interests on trustline update
                    assert (
                        last_standalone_balance_update is not None
                    ), "Found trustline update that should trigger balance update but did not find balance update"
                    apply_event_on_graph(graph, last_standalone_balance_update)
                    last_standalone_balance_update = None

                apply_event_on_graph(graph, event)

            elif event.type == TransferEventType:
                # The last standalone balance update is not due to mediation, but to a transfer from/to user
                assert (
                    last_standalone_balance_update is not None
                ), "Found transfer event but did not previously find balance update"
                apply_event_on_graph(graph, last_standalone_balance_update)
                last_standalone_balance_update = None

            elif event.type == BalanceUpdateEventType:
                event = cast(BalanceUpdateEvent, event)

                if last_standalone_balance_update is not None:
                    if (
                        event.blocknumber != last_standalone_balance_update.blocknumber
                        or event.transaction_index
                        != last_standalone_balance_update.transaction_index
                    ):
                        apply_event_on_graph(graph, last_standalone_balance_update)
                        last_standalone_balance_update = event
                        continue
                    else:
                        # We found a mediation from the user
                        safety_checks_on_mediated_transfer_balance_updates(
                            user_address, event, last_standalone_balance_update
                        )

                        fee = get_mediation_fee_from_balance_updates(
                            graph, user_address, last_standalone_balance_update, event
                        )
                        fees_earned.append(fee)

                        apply_event_on_graph(graph, event)
                        apply_event_on_graph(graph, last_standalone_balance_update)
                        last_standalone_balance_update = None
                else:
                    last_standalone_balance_update = event

            else:
                raise RuntimeError(f"Invalid event type received: {event.type}")

        return fees_earned

    def get_earned_mediation_fees_in_between_timestamps(
        self,
        user_address: str,
        graph: CurrencyNetworkGraph,
        start_time: int,
        end_time: Optional[int],
    ) -> List[MediationFee]:
        mediation_fees = self.get_earned_mediation_fees(user_address, graph)
        return filter_list_of_information_for_time_window(
            mediation_fees, start_time, end_time
        )

    def get_debt_lists_in_all_networks_with_path(
        self,
        user_address: str,
        currency_network_graphs: Dict[str, CurrencyNetworkGraph],
    ) -> List[DebtsListInCurrencyNetwork]:
        debts_list_in_all_networks = self.get_debt_lists_in_all_networks(user_address)
        return self.add_path_information_to_debt_lists(
            user_address, currency_network_graphs, debts_list_in_all_networks
        )

    def get_debt_lists_in_all_networks(
        self, user_address: str
    ) -> Dict[str, Dict[str, int]]:
        """
        Return a mapping from currency network to debts for user in currency network
        debts are a mapping from debtor to debt value
        """
        debt_update_events = self._currency_network_db.get_all_contract_events(
            user_address=user_address, event_types=[DebtUpdateEventType]
        )
        debt_update_events = sorted_events(debt_update_events)

        debts_in_all_currency_networks: Dict[str, Dict[str, int]] = {}
        for debt_update_event in debt_update_events:
            debt_update_event = cast(DebtUpdateEvent, debt_update_event)
            from_ = debt_update_event.from_
            to = debt_update_event.to
            debt_value = debt_update_event.debt
            network_address = debt_update_event.network_address

            if network_address not in debts_in_all_currency_networks.keys():
                debts_in_all_currency_networks[network_address] = {}

            if debt_update_event.to == user_address:
                if debt_value != 0:
                    debts_in_all_currency_networks[network_address][from_] = debt_value
                else:
                    clean_null_debt(
                        debts_in_all_currency_networks, network_address, from_
                    )

            elif from_ == user_address:
                if debt_value != 0:
                    debts_in_all_currency_networks[network_address][to] = -debt_value
                else:
                    clean_null_debt(debts_in_all_currency_networks, network_address, to)

            else:
                raise RuntimeError(
                    f"Found debt update where user_address {user_address}"
                    f" is neither `from_` nor `to`: {debt_update_event}."
                )

        return debts_in_all_currency_networks

    def add_path_information_to_debt_lists(
        self,
        user_address: str,
        currency_network_graphs: Dict[str, CurrencyNetworkGraph],
        debts_list_in_all_currency_networks: Dict[str, Dict[str, int]],
    ) -> List[DebtsListInCurrencyNetwork]:
        enriched_debts_lists_in_all_currency_networks = []
        for currency_network in debts_list_in_all_currency_networks.keys():
            enriched_debts_list = []

            for debtor in debts_list_in_all_currency_networks[currency_network].keys():
                debt_value = debts_list_in_all_currency_networks[currency_network][
                    debtor
                ]

                if debt_value > 0:
                    debt_claimer = user_address
                    debt_payer = debtor
                elif debt_value < 0:
                    debt_claimer = debtor
                    debt_payer = user_address
                else:
                    raise RuntimeError(f"Found null debt with debtor {debtor}")
                capacity_path = currency_network_graphs[
                    currency_network
                ].find_maximum_capacity_path(
                    debt_payer, debt_claimer, timestamp=int(time.time())
                )
                claimable_debt = min(capacity_path.capacity, abs(debt_value))

                debt = Debt(
                    debtor=debtor, value=debt_value, claimable_value=claimable_debt
                )

                if capacity_path.path != []:
                    debt.claim_path = capacity_path.path

                enriched_debts_list.append(debt)

            enriched_debts_lists_in_all_currency_networks.append(
                DebtsListInCurrencyNetwork(
                    currency_network=currency_network, debts_list=enriched_debts_list
                )
            )

        return enriched_debts_lists_in_all_currency_networks

    def get_total_sum_transferred(
        self, sender_address, receiver_address, start_time=0, end_time=None
    ):
        all_transfer_events = self._currency_network_db.get_events_from_to(
            event_types=[TransferEventType],
            start_time=start_time,
            end_time=end_time,
            from_address=sender_address,
            to_address=receiver_address,
        )
        sum = 0
        for event in all_transfer_events:
            assert (
                event.type == TransferEventType
            ), f"Expected event to be of type transfer: {event}"
            assert (
                event.from_ == sender_address
            ), f"Expected transfer sender to be {sender_address}: {event}"
            assert (
                event.to == receiver_address
            ), f"Expected transfer receiver to be {receiver_address}: {event}"
            sum += event.value
        return sum


def clean_null_debt(debts_in_all_currency_networks, network_address, debtor):
    del debts_in_all_currency_networks[network_address][debtor]
    if len(debts_in_all_currency_networks[network_address]) == 0:
        del debts_in_all_currency_networks[network_address]


def does_trustline_update_trigger_balance_update(
    graph: CurrencyNetworkGraph, trustline_update_event: TrustlineUpdateEvent
):
    # If the interests rate change and the balance was not 0
    # a BalanceUpdate event will be emitted due to application of interests
    trustline = graph.get_account_summary(
        trustline_update_event.from_,
        trustline_update_event.to,
        trustline_update_event.timestamp,
    )
    return trustline.balance != 0 and (
        trustline.interest_rate_given != trustline_update_event.interest_rate_given
        or trustline.interest_rate_received
        != trustline_update_event.interest_rate_received
    )


def get_mediation_fee_from_balance_updates(
    graph: CurrencyNetworkGraph,
    user_address: str,
    first_event: BalanceUpdateEvent,
    second_event: BalanceUpdateEvent,
) -> MediationFee:
    """
    Get the balance change of a user that mediated a transfer A -> user -> B
    The two events must be given as ordered by log index
    """
    assert (
        first_event.log_index == second_event.log_index - 1
    ), "Received unexpected non-consecutive events."

    first_balance_change = (
        graph.get_balance_with_interests(
            first_event.from_, first_event.to, first_event.timestamp,
        )
        - first_event.value
    )
    second_balance_change = (
        graph.get_balance_with_interests(
            second_event.from_, second_event.to, second_event.timestamp,
        )
        - second_event.value
    )
    fee_value = abs(second_balance_change - first_balance_change)

    if first_event.from_ == user_address:
        # transfer sender pays, emits first user->B and second A-> user
        transfer_sender = second_event.from_
        transfer_receiver = first_event.to
    elif first_event.to == user_address:
        # transfer receiver pays emits first A->user and second user->B
        transfer_sender = first_event.from_
        transfer_receiver = second_event.to
    else:
        raise RuntimeError("Could not find user_address in first_event.")

    fee = MediationFee(
        value=fee_value,
        from_=transfer_sender,
        to=transfer_receiver,
        transaction_hash=first_event.transaction_hash,
        timestamp=first_event.timestamp,
    )

    return fee


def safety_checks_on_mediated_transfer_balance_updates(
    user_address: str, first_event: BalanceUpdateEvent, second_event: BalanceUpdateEvent
):
    assert (
        first_event.timestamp == second_event.timestamp
    ), "Found a mediated transfer with events timestamp not matching"
    assert (
        first_event.blocknumber == second_event.blocknumber
    ), "Found a mediated transfer with events block number not matching"
    assert (
        abs(first_event.log_index - second_event.log_index) == 1
    ), "Found a mediated transfer with events log index difference greater than 1"
    if first_event.to == second_event.from_:
        assert first_event.to == user_address
    elif second_event.to == first_event.from_:
        assert second_event.to == user_address
    else:
        assert False, "Found a mediated transfer with to/from not matching"


def apply_event_on_graph(
    graph: CurrencyNetworkGraph, event: Union[TrustlineUpdateEvent, BalanceUpdateEvent]
):
    if event.type == TrustlineUpdateEventType:
        event = cast(TrustlineUpdateEvent, event)
        graph.update_trustline(
            event.from_,
            event.to,
            event.creditline_given,
            event.creditline_received,
            event.interest_rate_given,
            event.interest_rate_received,
        )
    elif event.type == BalanceUpdateEventType:
        event = cast(BalanceUpdateEvent, event)
        graph.update_balance(event.from_, event.to, event.value, event.timestamp)
    else:
        raise RuntimeError(
            f"Invalid event to be applied on graph, type received: {event.type}"
        )


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
        events,
        key=lambda event: (block_number_key(event), log_index_key(event)),
        reverse=reverse,
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
        if interest_value != 0:
            accrued_interests.append(
                InterestAccrued(
                    interest_value, interest_rate, post_balance_event.timestamp
                )
            )

    return accrued_interests


def filter_list_of_information_for_time_window(
    information_list: List, start_time: int = 0, end_time: Optional[int] = None
):
    if not end_time:
        end_time = int(time.time())
    filtered_list = []
    for information in information_list:
        if information.timestamp <= end_time and information.timestamp >= start_time:
            filtered_list.append(information)
    return filtered_list


def filter_events_with_type(all_events, event_type):
    return [event for event in all_events if event.type == event_type]


def filter_events_with_index(all_events, log_index):
    return [event for event in all_events if event.log_index == log_index]


def get_transfer_path(sorted_balance_updates):
    """Returns the transfer path of the given transfer without the sender"""
    path_from_events = []
    path_from_events.append(sorted_balance_updates[0].from_)
    path_from_events.extend(
        [balance_update.to for balance_update in sorted_balance_updates]
    )

    return path_from_events


def find_transfer_event(
    all_events: Iterable[BlockchainEvent], any_transfer_event: BlockchainEvent
) -> TransferEvent:
    """Finds the corresponding transfer event, where any_transfer_event can by any event of the transfer
    (BalanceUpdate or Transfer) and all_events should be already only potential BalanceUpdate and Transfer events.
    """

    log_index = any_transfer_event.log_index

    # Search forward for related Transfer update event
    # The contracts emit the events in the following order:
    # events = BalanceUpdate1, BalanceUpdate2, ... BalanceUpdateN, Transfer
    # They should be right next to each other, so the log_index should be like N, N+1, N+2, ...
    # If there is a gap, it is because it was not part of a Transfer, but for example part of a TrustlineUpdate
    relevant_events = list(
        sorted(
            [event for event in all_events if event.log_index >= log_index],
            key=attrgetter("log_index"),
        )
    )
    next_log_index = log_index

    for event in relevant_events:
        if event.log_index == next_log_index:
            # Found event that is potentially part of the transfer
            if event.type == TransferEventType:
                assert isinstance(event, TransferEvent)
                return event

            assert (
                event.type == BalanceUpdateEventType
            ), "Wrong event type for events before transfer event"

            next_log_index += 1
        else:  # There was a gap, so what we found is not a Transfer
            raise IdentifiedNotPartOfTransferException(
                block_hash=event.block_hash, log_index=log_index
            )
    else:  # No TransferEvent found, so no Transfer
        raise IdentifiedNotPartOfTransferException(
            block_hash=event.block_hash, log_index=log_index
        )


def get_balance_update_events_for_transfer(
    all_events: Iterable[BlockchainEvent], transfer_event: TransferEvent
) -> List[BalanceUpdateEvent]:
    """Returns all balance update events in the correct order that belongs to the transfer event"""
    log_index = transfer_event.log_index
    sender = transfer_event.from_
    receiver = transfer_event.to

    balance_events: List[BalanceUpdateEvent] = []
    saw_sender_event = False
    saw_receiver_event = False

    # Search backwards for related BalanceUpdate events
    # The events of a transfer are in the following order without gaps
    # events = BalanceUpdate1, BalanceUpdate2, ... BalanceUpdateN, Transfer
    relevant_events = [event for event in all_events if event.log_index < log_index]
    relevant_events.sort(key=attrgetter("log_index"), reverse=True)

    next_log_index = log_index - 1
    for event in relevant_events:
        assert event.type == BalanceUpdateEventType and isinstance(
            event, BalanceUpdateEvent
        ), "Wrong event type for events before transfer event"
        assert (
            event.log_index == next_log_index
        ), f"Logindex is not as expected, {event.log_index} instead of {next_log_index}"
        balance_events.append(event)
        if event.to == receiver:
            saw_receiver_event = True
        if event.from_ == sender:
            saw_sender_event = True
        if saw_sender_event and saw_receiver_event:
            break
        next_log_index -= 1
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
    return event.block_hash, event.log_index


class TransferNotFoundException(Exception):
    def __init__(self, *, tx_hash=None):
        self.tx_hash = tx_hash


class EventNotFoundException(Exception):
    def __init__(self, *, block_hash=None, log_index=None):
        self.block_hash = block_hash
        self.log_index = log_index


class IdentifiedNotPartOfTransferException(Exception):
    def __init__(self, *, block_hash=None, log_index=None):
        self.block_hash = block_hash
        self.log_index = log_index
