import functools
import itertools
import logging
import socket
from typing import List, NamedTuple

import gevent

import relay.concurrency_utils as concurrency_utils

from .currency_network_events import (
    BalanceUpdateEventType,
    CurrencyNetworkEvent,
    TransferEventType,
    TrustlineRequestEventType,
    TrustlineUpdateEventType,
    event_builders,
    from_to_types,
    standard_event_types,
)
from .events import BlockchainEvent
from .proxy import Proxy, reconnect_interval, sorted_events


class Trustline(NamedTuple):
    user: str
    counter_party: str
    creditline_given: int = 0
    creditline_received: int = 0
    interest_rate_given: int = 0
    interest_rate_received: int = 0
    is_frozen: bool = False
    fees_outstanding_user: int = 0
    fees_outstanding_counter_party: int = 0
    m_time: int = 0
    balance: int = 0


logger = logging.getLogger("currency network")


class CurrencyNetworkProxy(Proxy):

    event_builders = event_builders
    event_types = list(event_builders.keys())

    standard_event_types = standard_event_types

    def __init__(self, web3, abi, address: str) -> None:
        super().__init__(web3, abi, address)
        self.name: str = self._proxy.functions.name().call().strip("\0")
        self.decimals: int = self._proxy.functions.decimals().call()
        self.symbol: str = self._proxy.functions.symbol().call().strip("\0")
        self.capacity_imbalance_fee_divisor = (
            self._proxy.functions.capacityImbalanceFeeDivisor().call()
        )
        self.default_interest_rate = self._proxy.functions.defaultInterestRate().call()
        self.custom_interests = self._proxy.functions.customInterests().call()
        self.prevent_mediator_interests = (
            self._proxy.functions.preventMediatorInterests().call()
        )
        # Fixed for now, see contracts
        self.interest_rate_decimals = 2

    @property
    def users(self) -> List[str]:
        return list(self._proxy.functions.getUsers().call())

    @property
    def num_users(self) -> int:
        return len(self.users)

    def friends(self, user_address: str) -> List[str]:
        return list(self._proxy.functions.getFriends(user_address).call())

    def account(self, a_address: str, b_address: str):
        return self._proxy.functions.getAccount(a_address, b_address).call()

    def spendable(self, a_address: str):
        return self._proxy.functions.spendable(a_address).call()

    def spendableTo(self, a_address: str, b_address: str):
        return self._proxy.functions.spendableTo(a_address, b_address).call()

    def gen_graph_representation(self) -> List[Trustline]:
        """Returns the trustlines network as a dict address -> list of Friendships"""
        result = []
        for user in self.users:
            for friend in self.friends(user):
                if user < friend:
                    (
                        creditline_ab,
                        creditline_ba,
                        interest_ab,
                        interest_ba,
                        is_frozen,
                        fees_outstanding_a,
                        fees_outstanding_b,
                        mtime,
                        balance_ab,
                    ) = self.account(user, friend)
                    result.append(
                        Trustline(
                            user=user,
                            counter_party=friend,
                            creditline_given=creditline_ab,
                            creditline_received=creditline_ba,
                            interest_rate_given=interest_ab,
                            interest_rate_received=interest_ba,
                            is_frozen=is_frozen,
                            fees_outstanding_user=fees_outstanding_a,
                            fees_outstanding_counter_party=fees_outstanding_b,
                            m_time=mtime,
                            balance=balance_ab,
                        )
                    )
        return result

    def start_listen_on_full_sync(self, function, sync_interval: float):
        def sync():
            while True:
                try:
                    function(self.gen_graph_representation())
                    gevent.sleep(sync_interval)
                except socket.timeout as err:
                    logger.warning(
                        "Full sync failed because of timeout, try again: " + str(err)
                    )
                    gevent.sleep(reconnect_interval)
                except socket.error as err:
                    logger.warning(
                        "Full sync failed because of error, try again: " + str(err)
                    )
                    gevent.sleep(reconnect_interval)

        gevent.Greenlet.spawn(sync)

    def start_listen_on_balance(self, on_balance) -> None:
        def log(log_entry):
            on_balance(self._build_event(log_entry))

        self.start_listen_on(BalanceUpdateEventType, log)

    def start_listen_on_trustline(self, on_trustline_change) -> None:
        def log_trustline(log_entry):
            on_trustline_change(self._build_event(log_entry))

        self.start_listen_on(TrustlineUpdateEventType, log_trustline)

    def start_listen_on_trustline_request(self, on_trustline_request) -> None:
        def log_trustline_request(log_entry):
            on_trustline_request(self._build_event(log_entry))

        self.start_listen_on(TrustlineRequestEventType, log_trustline_request)

    def start_listen_on_transfer(self, on_transfer) -> None:
        def log(log_entry):
            on_transfer(self._build_event(log_entry))

        self.start_listen_on(TransferEventType, log)

    def get_network_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
    ) -> List[BlockchainEvent]:
        logger.debug(
            "get_network_events: event_name=%s user_address=%s from_block=%s",
            event_name,
            user_address,
            from_block,
        )
        if user_address is None:
            queries = [
                functools.partial(self.get_events, event_name, from_block=from_block)
            ]
            events = concurrency_utils.joinall(queries, timeout=timeout)
        else:

            filter1 = {from_to_types[event_name][0]: user_address}
            filter2 = {from_to_types[event_name][1]: user_address}

            queries = [
                functools.partial(self.get_events, event_name, filter1, from_block),
                functools.partial(self.get_events, event_name, filter2, from_block),
            ]
            results = concurrency_utils.joinall(queries, timeout=timeout)

            events = list(itertools.chain.from_iterable(results))

            for event in events:
                if isinstance(event, CurrencyNetworkEvent):
                    event.user = user_address
                else:
                    raise ValueError("Expected a CurrencyNetworkEvent")
        return sorted_events(events)

    def get_all_network_events(
        self, user_address: str = None, from_block: int = 0, timeout: float = None
    ) -> List[BlockchainEvent]:
        queries = [
            functools.partial(
                self.get_network_events,
                type,
                user_address=user_address,
                from_block=from_block,
            )
            for type in self.standard_event_types
        ]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))
