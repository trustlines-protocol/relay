import logging
from typing import List

import gevent
import itertools
from .proxy import Proxy, sorted_events
from relay.logger import get_logger

from .token_events import (
    BlockchainEvent,
    TokenEvent,
    TransferEventType,
    ApprovalEventType,
    from_to_types,
    event_builders
)

logger = get_logger('token', logging.DEBUG)

TransferEvent = 'Transfer'
ApprovalEvent = 'Approval'


class TokenProxy(Proxy):

    def __init__(self, web3, token_abi, address: str) -> None:
        super().__init__(web3, token_abi, address)

    def balance_of(self, user_address: str):
        return self._proxy.call().balanceOf(user_address)

    def get_token_events(self, event_name: str, user_address: str=None, from_block: int=0) -> List[BlockchainEvent]:
        if user_address is None:
            result = self.get_events(event_name, from_block=from_block)
        else:
            filter1 = {from_to_types[event_name][0]: user_address}

            if event_name is TransferEvent:
                filter2 = {from_to_types[event_name][1]: user_address}
                events = [
                    gevent.spawn(self.get_events, event_name, filter1, from_block),
                    gevent.spawn(self.get_events, event_name, filter2, from_block)
                ]
                gevent.joinall(events, timeout=2)
                result = list(itertools.chain.from_iterable([event.value for event in events]))
            else:
                result = self.get_events(event_name, filter1, from_block)

            for event in result:
                if isinstance(event, TokenEvent):
                    event.user = user_address
                else:
                    raise ValueError('Expected a UnwEthEvent')
        return sorted_events(result)

    def get_all_token_events(self, user_address: str = None, from_block: int = 0) -> List[BlockchainEvent]:
        events = [gevent.spawn(self.get_token_events,
                               type,
                               user_address=user_address,
                               from_block=from_block) for type in self.standard_event_types]
        gevent.joinall(events, timeout=5)
        return sorted_events(list(itertools.chain.from_iterable([event.value for event in events])))
