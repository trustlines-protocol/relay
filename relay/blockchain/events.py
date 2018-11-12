from typing import Optional

import hexbytes

from ..events import Event


class BlockchainEvent(Event):

    def __init__(self, web3_event, current_blocknumber: int, timestamp: int) -> None:
        super().__init__(timestamp)
        self._web3_event = web3_event
        self.blocknumber: Optional[int] = web3_event.get('blockNumber', None)
        self._current_blocknumber = current_blocknumber
        # NOTE: The field transactionHash is of type HexBytes sind web3 v4. It can also be a hex string because
        # the indexer currently can not save bytes in the database.
        # See issue https://github.com/trustlines-network/py-eth-index/issues/16
        self.transaction_id: hexbytes.HexBytes
        transaction_id = web3_event.get('transactionHash')
        if not isinstance(transaction_id, hexbytes.HexBytes):
            self.transaction_id = hexbytes.HexBytes(web3_event.get('transactionHash'))
        else:
            self.transaction_id = transaction_id
        self.type = web3_event.get('event')

    @property
    def status(self) -> str:
        if self.blocknumber is None:
            return 'sent'
        elif (self._current_blocknumber - self.blocknumber) < 5:
            return 'pending'
        else:
            return 'confirmed'


class TLNetworkEvent(BlockchainEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, from_to_types, user=None) -> None:
        super().__init__(web3_event, current_blocknumber, timestamp)
        self.user = user
        self.from_to_types = from_to_types

    @property
    def from_(self) -> str:
        return self._web3_event.get('args')[self.from_to_types[self._web3_event.get('event')][0]]

    @property
    def to(self) -> str:
        return self._web3_event.get('args')[self.from_to_types[self._web3_event.get('event')][1]]

    @property
    def direction(self):
        if self.user is None:
            return None
        if self.from_ == self.user:
            return 'sent'
        else:
            return 'received'

    @property
    def counter_party(self):
        if self.user is None:
            return None
        if self.from_ == self.user:
            return self.to
        else:
            return self.from_
