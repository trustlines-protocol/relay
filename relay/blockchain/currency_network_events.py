import hexbytes

from .events import TLNetworkEvent

TrustlineRequestEventType = "TrustlineUpdateRequest"
TrustlineUpdateEventType = "TrustlineUpdate"
BalanceUpdateEventType = "BalanceUpdate"
TransferEventType = "Transfer"


class CurrencyNetworkEvent(TLNetworkEvent):
    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(
            web3_event, current_blocknumber, timestamp, from_to_types, user
        )
        self.network_address = web3_event.get("address")


class ValueEvent(CurrencyNetworkEvent):
    @property
    def value(self):
        return self._web3_event.get("args").get("_value")


class TransferEvent(ValueEvent):
    @property
    def extra_data(self):
        extra_data = self._web3_event.get("args").get("_extraData")
        # NOTE: The argument extraData can be a hex string because the indexer currently can
        #       not save bytes in the database. See issue https://github.com/trustlines-protocol/py-eth-index/issues/16
        if not isinstance(extra_data, hexbytes.HexBytes):
            return hexbytes.HexBytes(extra_data)
        else:
            return extra_data


class BalanceUpdateEvent(ValueEvent):
    pass


class TrustlineEvent(CurrencyNetworkEvent):
    @property
    def creditline_given(self):
        return self._web3_event.get("args").get("_creditlineGiven")

    @property
    def creditline_received(self):
        return self._web3_event.get("args").get("_creditlineReceived")

    @property
    def interest_rate_given(self):
        return self._web3_event.get("args").get("_interestRateGiven", 0)

    @property
    def interest_rate_received(self):
        return self._web3_event.get("args").get("_interestRateReceived", 0)

    @property
    def is_frozen(self):
        return self._web3_event.get("args").get("_isFrozen")


class TrustlineUpdateEvent(TrustlineEvent):
    pass


class TrustlineRequestEvent(TrustlineEvent):
    pass


event_builders = {
    TransferEventType: TransferEvent,
    TrustlineUpdateEventType: TrustlineUpdateEvent,
    TrustlineRequestEventType: TrustlineRequestEvent,
    BalanceUpdateEventType: BalanceUpdateEvent,
}


from_to_types = {
    TransferEventType: ["_from", "_to"],
    TrustlineRequestEventType: ["_creditor", "_debtor"],
    TrustlineUpdateEventType: ["_creditor", "_debtor"],
    BalanceUpdateEventType: ["_from", "_to"],
}

standard_event_types = [
    TransferEventType,
    TrustlineRequestEventType,
    TrustlineUpdateEventType,
]
