import logging
import socket
from collections import namedtuple
from typing import List, Dict
import functools
import itertools

import gevent

import relay.concurrency_utils as concurrency_utils
from .proxy import Proxy, reconnect_interval, sorted_events
from relay.logger import get_logger
from web3.exceptions import BadFunctionCallOutput, ValidationError, MismatchedABI

from .events import BlockchainEvent
from .currency_network_events import (
    CurrencyNetworkEvent,
    TrustlineUpdateEventType,
    TrustlineRequestEventType,
    BalanceUpdateEventType,
    TransferEventType,
    from_to_types,
    event_builders,
    standard_event_types
)


class Trustline(namedtuple('Trustline',
                           ['address', 'creditline_ab', 'creditline_ba', 'interest_ab', 'interest_ba',
                            'fees_outstanding_a', 'fees_outstanding_b', 'm_time', 'balance_ab'])):
    __slots__ = ()

    def __new__(cls, address, creditline_ab=0, creditline_ba=0, interest_ab=0, interest_ba=0, fees_outstanding_a=0,
                fees_outstanding_b=0, m_time=0, balance_ab=0):
        return super(Trustline, cls).__new__(cls, address, creditline_ab, creditline_ba, interest_ab, interest_ba,
                                             fees_outstanding_a, fees_outstanding_b, m_time, balance_ab)


logger = get_logger('currency network', logging.DEBUG)


class CurrencyNetworkProxy(Proxy):

    event_builders = event_builders
    event_types = list(event_builders.keys())

    standard_event_types = standard_event_types

    def __init__(self, web3, abi, address: str) -> None:
        super().__init__(web3, abi, address)
        self.name: str = self._proxy.functions.name().call().strip('\0')
        self.decimals: int = self._proxy.functions.decimals().call()
        self.symbol: str = self._proxy.functions.symbol().call().strip('\0')
        try:
            self.capacity_imbalance_fee_divisor = self._proxy.functions.capacityImbalanceFeeDivisor().call()
        except (BadFunctionCallOutput, ValidationError, MismatchedABI) as e:
            self.capacity_imbalance_fee_divisor = 100

        try:
            self.default_interest_rate = self._proxy.functions.defaultInterestRate().call()
        except (BadFunctionCallOutput, ValidationError, MismatchedABI) as e:
            self.default_interest_rate = 0

        try:
            self.custom_interests = self._proxy.functions.customInterests().call()
        except (BadFunctionCallOutput, ValidationError, MismatchedABI) as e:
            self.custom_interests = False

        try:
            self.prevent_mediator_interests = self._proxy.functions.preventMediatorInterests().call()
        except (BadFunctionCallOutput, ValidationError, MismatchedABI) as e:
            self.prevent_mediator_interests = False
        self.interest_rate_decimals = 2  # Fixed for now, see contracts

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

    def gen_graph_representation(self) -> Dict[str, List[Trustline]]:
        """Returns the trustlines network as a dict address -> list of Friendships"""
        result = {}
        for user in self.users:
            list = []
            for friend in self.friends(user):
                if user < friend:
                    (creditline_ab,
                     creditline_ba,
                     interest_ab,
                     interest_ba,
                     fees_outstanding_a,
                     fees_outstanding_b,
                     mtime,
                     balance_ab) = self.account(user, friend)
                    list.append(Trustline(friend,
                                          creditline_ab,
                                          creditline_ba,
                                          interest_ab,
                                          interest_ba,
                                          fees_outstanding_a,
                                          fees_outstanding_b,
                                          mtime,
                                          balance_ab))
            result[user] = list
        return result

    def start_listen_on_full_sync(self, function, sync_interval: float):
        def sync():
            while True:
                try:
                    function(self.gen_graph_representation())
                    gevent.sleep(sync_interval)
                except socket.timeout as err:
                    logger.warning('Full sync failed because of timeout, try again: ' + str(err))
                    gevent.sleep(reconnect_interval)
                except socket.error as err:
                    logger.warning('Full sync failed because of error, try again: ' + str(err))
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

    def get_network_events(self,
                           event_name: str,
                           user_address: str=None,
                           from_block: int=0,
                           timeout: float = None
                           ) -> List[BlockchainEvent]:
        logger.debug("get_network_events: event_name=%s user_address=%s from_block=%s",
                     event_name,
                     user_address,
                     from_block)
        if user_address is None:
            queries = [functools.partial(self.get_events, event_name, from_block=from_block)]
            events = concurrency_utils.joinall(queries, timeout=timeout)
        else:

            filter1 = {from_to_types[event_name][0]: user_address}
            filter2 = {from_to_types[event_name][1]: user_address}

            queries = [
                functools.partial(self.get_events, event_name, filter1, from_block),
                functools.partial(self.get_events, event_name, filter2, from_block)
            ]
            results = concurrency_utils.joinall(queries, timeout=timeout)

            events = list(itertools.chain.from_iterable(results))

            for event in events:
                if isinstance(event, CurrencyNetworkEvent):
                    event.user = user_address
                else:
                    raise ValueError('Expected a CurrencyNetworkEvent')
        return sorted_events(events)

    def get_all_network_events(self,
                               user_address: str = None,
                               from_block: int = 0,
                               timeout: float = None
                               ) -> List[BlockchainEvent]:
        queries = [functools.partial(self.get_network_events,
                                     type,
                                     user_address=user_address,
                                     from_block=from_block) for type in self.standard_event_types]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))

    def estimate_gas_for_transfer(self, sender, receiver, value, max_fee, path):
        return self._proxy.estimateGas({'from': sender}).transfer(receiver, value, max_fee, path)

    def estimate_gas_for_payment_path(self, payment_path):
        """estimate gas for doing a transfer for the given payment_path"""
        if not payment_path.path:
            return 0
        source = payment_path.path[0]
        target = payment_path.path[-1]
        return self._proxy.estimateGas({'from': source}).transfer(target,
                                                                  payment_path.value,
                                                                  payment_path.fee,
                                                                  payment_path.path[1:])
