import logging
from typing import List
import functools
import itertools

import relay.concurrency_utils as concurrency_utils
from .proxy import Proxy, sorted_events
from relay.logger import get_logger
from .events import BlockchainEvent
from .unw_eth_events import (
    UnwEthEvent,
    TransferEventType,
    from_to_types,
    event_builders,
    standard_event_types,
)

logger = get_logger('unwrap eth', logging.DEBUG)


class UnwEthProxy(Proxy):

    event_builders = event_builders
    event_types = list(event_builders.keys())

    standard_event_types = standard_event_types

    def __init__(self, web3, unw_eth_abi, address: str) -> None:
        super().__init__(web3, unw_eth_abi, address)

    def balance_of(self, user_address: str):
        return self._proxy.call().balanceOf(user_address)

    def get_unw_eth_events(self,
                           event_name: str,
                           user_address: str=None,
                           from_block: int=0,
                           timeout: float=None) -> List[BlockchainEvent]:
        logger.debug("get_unw_eth_events: event_name=%s user_address=%s from_block=%s",
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
                if isinstance(event, UnwEthEvent):
                    event.user = user_address
                else:
                    raise ValueError('Expected a UnwEthEvent')
        return sorted_events(events)

    def get_all_unw_eth_events(self,
                               user_address: str = None,
                               from_block: int = 0,
                               timeout: float = None) -> List[BlockchainEvent]:
        queries = [functools.partial(self.get_unw_eth_events,
                                     type,
                                     user_address=user_address,
                                     from_block=from_block) for type in self.standard_event_types]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))
