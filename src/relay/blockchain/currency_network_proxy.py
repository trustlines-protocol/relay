import logging
from typing import List, NamedTuple

from gevent import Greenlet

from .currency_network_events import (
    TransferEventType,
    TrustlineRequestCancelEventType,
    TrustlineRequestEventType,
    TrustlineUpdateEventType,
    event_builders,
)
from .proxy import Proxy


class Trustline(NamedTuple):
    user: str
    counter_party: str
    creditline_given: int = 0
    creditline_received: int = 0
    interest_rate_given: int = 0
    interest_rate_received: int = 0
    is_frozen: bool = False
    m_time: int = 0
    balance: int = 0


logger = logging.getLogger("currency network")


class CurrencyNetworkProxy(Proxy):

    event_builders = event_builders

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

    def fetch_users(self) -> List[str]:
        return list(self._proxy.functions.getUsers().call())

    def fetch_num_users(self) -> int:
        return len(self.fetch_users())

    def fetch_friends(self, user_address: str) -> List[str]:
        return list(self._proxy.functions.getFriends(user_address).call())

    def fetch_account(self, a_address: str, b_address: str):
        return self._proxy.functions.getAccount(a_address, b_address).call()

    def fetch_is_frozen_status(self):
        return self._proxy.functions.isNetworkFrozen().call()

    def gen_graph_representation(self) -> List[Trustline]:
        """Returns the trustlines network as a dict address -> list of Friendships"""
        result = []
        for user in self.fetch_users():
            for friend in self.fetch_friends(user):
                if user < friend:
                    (
                        creditline_ab,
                        creditline_ba,
                        interest_ab,
                        interest_ba,
                        is_frozen,
                        mtime,
                        balance_ab,
                    ) = self.fetch_account(user, friend)
                    result.append(
                        Trustline(
                            user=user,
                            counter_party=friend,
                            creditline_given=creditline_ab,
                            creditline_received=creditline_ba,
                            interest_rate_given=interest_ab,
                            interest_rate_received=interest_ba,
                            is_frozen=is_frozen,
                            m_time=mtime,
                            balance=balance_ab,
                        )
                    )
        return result

    def start_listen_on_trustline(
        self, on_trustline_change, *, start_log_filter=True
    ) -> Greenlet:
        def log_trustline(log_entry):
            on_trustline_change(self._build_event(log_entry))

        return self.start_listen_on(
            TrustlineUpdateEventType, log_trustline, start_log_filter=start_log_filter
        )

    def start_listen_on_trustline_request(
        self, on_trustline_request, *, start_log_filter=True
    ) -> Greenlet:
        def log_trustline_request(log_entry):
            on_trustline_request(self._build_event(log_entry))

        return self.start_listen_on(
            TrustlineRequestEventType,
            log_trustline_request,
            start_log_filter=start_log_filter,
        )

    def start_listen_on_trustline_request_cancel(
        self, on_trustline_request_cancel, *, start_log_filter=True
    ) -> Greenlet:
        def log_trustline_request_cancel(log_entry):
            on_trustline_request_cancel(self._build_event(log_entry))

        return self.start_listen_on(
            TrustlineRequestCancelEventType,
            log_trustline_request_cancel,
            start_log_filter=start_log_filter,
        )

    def start_listen_on_transfer(
        self, on_transfer, *, start_log_filter=True
    ) -> Greenlet:
        def log(log_entry):
            on_transfer(self._build_event(log_entry))

        return self.start_listen_on(
            TransferEventType, log, start_log_filter=start_log_filter
        )
