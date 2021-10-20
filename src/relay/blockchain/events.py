from typing import Optional

import hexbytes

from ..events import Event


class BlockchainEvent(Event):
    def __init__(self, web3_event, current_blocknumber: int, timestamp: int) -> None:
        super().__init__(timestamp)
        self._web3_event = web3_event
        self.blocknumber: Optional[int] = web3_event.get("blockNumber", None)
        self._current_blocknumber = current_blocknumber
        event_block_hash = web3_event.get("blockHash", None)
        if event_block_hash:
            self.block_hash: Optional[hexbytes.HexBytes] = _field_to_hexbytes(
                event_block_hash
            )
        else:
            self.block_hash = None
        self.transaction_hash = _field_to_hexbytes(web3_event.get("transactionHash"))
        self.type = web3_event.get("event")
        self.log_index = web3_event.get("logIndex")
        self.transaction_index = web3_event.get("transactionIndex")

    @property
    def status(self) -> str:
        if self.blocknumber is None:
            return "sent"
        elif (self._current_blocknumber - self.blocknumber) < 5:
            return "pending"
        else:
            return "confirmed"


class TLNetworkEvent(BlockchainEvent):
    def __init__(
        self, web3_event, current_blocknumber, timestamp, from_to_types, user=None
    ) -> None:
        super().__init__(web3_event, current_blocknumber, timestamp)
        self.user = user
        self.from_to_types = from_to_types

    @property
    def from_(self) -> str:
        return self._web3_event.get("args")[
            self.from_to_types[self._web3_event.get("event")][0]
        ]

    @property
    def to(self) -> str:
        return self._web3_event.get("args")[
            self.from_to_types[self._web3_event.get("event")][1]
        ]

    @property
    def direction(self):
        if self.user is None:
            return None
        if self.from_ == self.user:
            return "sent"
        else:
            return "received"

    @property
    def counter_party(self):
        if self.user is None:
            return None
        if self.from_ == self.user:
            return self.to
        else:
            return self.from_


def _field_to_hexbytes(field_value) -> hexbytes.HexBytes:
    # NOTE: Some fields are of type HexBytes since web3 v4. It can also be a hex string because
    # the indexer currently can not save bytes in the database.
    # See issue https://github.com/trustlines-protocol/py-eth-index/issues/16
    if not isinstance(field_value, hexbytes.HexBytes):
        return hexbytes.HexBytes(field_value)
    else:
        return field_value
