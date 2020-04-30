from .events import BlockchainEvent

FeePaymentEventType = "FeePayment"


class FeePaymentEvent(BlockchainEvent):
    @property
    def value(self):
        return self._web3_event.get("args").get("value")

    @property
    def from_(self):
        return self._web3_event.get("address")

    @property
    def to(self):
        return self._web3_event.get("args").get("recipient")

    @property
    def currency_network(self):
        return self._web3_event.get("args").get("currencyNetwork")


event_builders = {
    FeePaymentEventType: FeePaymentEvent,
}
