import logging
from typing import List
import functools
import itertools

import relay.concurrency_utils as concurrency_utils
from .proxy import Proxy, sorted_events
from relay.logger import get_logger
from .events import BlockchainEvent
from .token_events import (
    TokenEvent,
    TransferEventType,
    from_to_types,
    event_builders,
    standard_event_types,
)

logger = get_logger('token', logging.DEBUG)


class TokenProxy(Proxy):

    event_builders = event_builders
    event_types = list(event_builders.keys())

    standard_event_types = standard_event_types

    def __init__(self, web3, token_abi, address: str) -> None:
        super().__init__(web3, token_abi, address)

    def balance_of(self, user_address: str):
        return self._proxy.functions.balanceOf(user_address).call()

    def get_token_events(self,
                         event_name: str,
                         user_address: str=None,
                         from_block: int=0,
                         timeout: float=None) -> List[BlockchainEvent]:
        logger.debug("get_token_events: event_name=%s user_address=%s from_block=%s",
                     event_name,
                     user_address,
                     from_block)
        if user_address is None:
            queries = [functools.partial(self.get_events, event_name, from_block=from_block)]
            events = concurrency_utils.joinall(queries, timeout=timeout)
        else:
            filter1 = {from_to_types[event_name][0]: user_address}
            filter2 = {from_to_types[event_name][1]: user_address}

            queries = [functools.partial(self.get_events, event_name, filter1, from_block)]
            if (event_name == TransferEventType):
                queries.append(functools.partial(self.get_events, event_name, filter2, from_block))
            results = concurrency_utils.joinall(queries, timeout=timeout)

            events = list(itertools.chain.from_iterable(results))

            for event in events:
                if isinstance(event, TokenEvent):
                    event.user = user_address
                else:
                    raise ValueError('Expected a TokenEvent')
        return sorted_events(events)

    def get_all_token_events(self,
                             user_address: str = None,
                             from_block: int = 0,
                             timeout: float=None) -> List[BlockchainEvent]:
        queries = [functools.partial(self.get_token_events,
                                     type,
                                     user_address=user_address,
                                     from_block=from_block) for type in self.standard_event_types]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))
