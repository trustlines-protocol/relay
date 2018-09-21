import logging
from typing import List
import functools
import itertools

import relay.concurrency_utils as concurrency_utils
from .proxy import Proxy, sorted_events
from relay.logger import get_logger

from relay.exchange.order import Order
from .exchange_events import (
    BlockchainEvent,
    ExchangeEvent,
    LogFillEventType,
    LogCancelEventType,
    from_to_types,
    event_builders,
    standard_event_types
)

logger = get_logger('token', logging.DEBUG)


class ExchangeProxy(Proxy):

    event_builders = event_builders
    event_types = list(event_builders.keys())
    standard_event_types = standard_event_types

    def __init__(self, web3, exchange_abi, token_abi, address: str, address_oracle) -> None:
        super().__init__(web3, exchange_abi, address)
        self._token_abi = token_abi
        self._address_oracle = address_oracle

    def validate(self, order: Order) -> bool:
        return (order.exchange_address == self.address and
                self.validate_funds(order) and
                self.validate_filled_amount(order))

    def validate_funds(self, order: Order) -> bool:
        if self._is_currency_network(order.maker_token):
            return True
        else:
            maker_token = self._token_contract(address=order.maker_token)
            return (maker_token.functions.balanceOf(order.maker_address).call() >= order.maker_token_amount and
                    (self._is_trusted_token(order.maker_token) or
                     maker_token.functions.allowance(order.maker_address,
                                                     self.address).call() >= order.maker_token_amount))

    def validate_filled_amount(self, order: Order) -> bool:
        return self._proxy.functions.getUnavailableTakerTokenAmount(order.hash()).call() < order.taker_token_amount

    def get_filled_amount(self, order: Order) -> int:
        return self._proxy.functions.filled(order.hash()).call()

    def get_cancelled_amount(self, order: Order) -> int:
        return self._proxy.functions.cancelled(order.hash()).call()

    def get_unavailable_amount(self, order: Order) -> int:
        return self._proxy.functions.getUnavailableTakerTokenAmount(order.hash()).call()

    def start_listen_on_fill(self, f) -> None:
        def log(log_entry):
            f(log_entry['args']['orderHash'],
              log_entry['args']['filledMakerTokenAmount'],
              log_entry['args']['filledTakerTokenAmount'])
        self.start_listen_on(LogFillEventType, log)

    def start_listen_on_cancel(self, f) -> None:
        def log(log_entry):
            f(log_entry['args']['orderHash'],
              log_entry['args']['cancelledMakerTokenAmount'],
              log_entry['args']['cancelledTakerTokenAmount'])
        self.start_listen_on(LogCancelEventType, log)

    def get_exchange_events(self,
                            event_name: str,
                            user_address: str=None,
                            from_block: int=0,
                            timeout: float=None) -> List[BlockchainEvent]:
        logger.debug("get_exchange_events: event_name=%s user_address=%s from_block=%s",
                     event_name,
                     user_address,
                     from_block)
        if user_address is None:
            queries = [functools.partial(self.get_events, event_name, from_block=from_block)]
            events = concurrency_utils.joinall(queries, timeout=timeout)
        else:
            filter1 = {from_to_types[event_name][0]: user_address}
            # filter2 = {from_to_types[event_name][1]: user_address}

            queries = [functools.partial(self.get_events, event_name, filter1, from_block)]
            # TODO taker attribute of LogFill is not indexed in contract yet
            # if event_name == LogFillEventType:
            #   queries.append(functools.partial(self.get_events, event_name, filter2, from_block))
            results = concurrency_utils.joinall(queries, timeout=timeout)

            events = list(itertools.chain.from_iterable(results))

            for event in events:
                if isinstance(event, ExchangeEvent):
                    event.user = user_address
                else:
                    raise ValueError('Expected a ExchangeEvent')
        return sorted_events(events)

    def get_all_exchange_events(self,
                                user_address: str=None,
                                from_block: int=0,
                                timeout: float=None) -> List[BlockchainEvent]:
        queries = [functools.partial(self.get_exchange_events,
                                     type,
                                     user_address=user_address,
                                     from_block=from_block) for type in self.standard_event_types]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))

    def _is_currency_network(self, token_address: str) -> bool:
        return self._address_oracle.is_currency_network(token_address)

    def _is_trusted_token(self, token_address: str) -> bool:
        return self._address_oracle.is_trusted_token(token_address)

    def _token_contract(self, address: str):
        return self._web3.eth.contract(abi=self._token_abi, address=address)


class DummyExchangeProxy():

    def __init__(self, exchange_address: str) -> None:
        self.address = exchange_address

    def validate(self, order: Order) -> bool:
        return True

    def validate_funds(self, order: Order) -> bool:
        return True

    def validate_filled_amount(self, order: Order) -> bool:
        return True

    def get_filled_amount(self, order: Order) -> int:
        return 0

    def start_listen_on_fill(self, f) -> None:
        pass

    def start_listen_on_cancel(self, f) -> None:
        pass
