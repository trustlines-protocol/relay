from .events import TLNetworkEvent


CreditlineRequestEventType = 'CreditlineUpdateRequest'
CreditlineUpdateEventType = 'CreditlineUpdate'
TrustlineRequestEventType = 'TrustlineUpdateRequest'
TrustlineUpdateEventType = 'TrustlineUpdate'
BalanceUpdateEventType = 'BalanceUpdate'
TransferEventType = 'Transfer'


class CurrencyNetworkEvent(TLNetworkEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(web3_event, current_blocknumber, timestamp, from_to_types, user)
        self.network_address = web3_event.get('address')


class ValueEvent(CurrencyNetworkEvent):

    @property
    def value(self):
        return self._web3_event.get('args').get('_value')


class TransferEvent(ValueEvent):
    pass


class BalanceUpdateEvent(ValueEvent):
    pass


class CreditlineUpdateEvent(ValueEvent):
    pass


class CreditlineRequestEvent(ValueEvent):
    pass


class TrustlineEvent(CurrencyNetworkEvent):

    @property
    def given(self):
        return self._web3_event.get('args').get('_creditlineGiven')

    @property
    def received(self):
        return self._web3_event.get('args').get('_creditlineReceived')


class TrustlineUpdateEvent(TrustlineEvent):
    pass


class TrustlineRequestEvent(TrustlineEvent):
    pass


event_builders = {
    TransferEventType: TransferEvent,
    CreditlineRequestEventType: CreditlineRequestEvent,
    CreditlineUpdateEventType: CreditlineUpdateEvent,
    TrustlineUpdateEventType: TrustlineUpdateEvent,
    TrustlineRequestEventType: TrustlineRequestEvent,
    BalanceUpdateEventType: BalanceUpdateEvent,
}


from_to_types = {
    TransferEventType: ['_from', '_to'],
    CreditlineRequestEventType: ['_creditor', '_debtor'],
    CreditlineUpdateEventType: ['_creditor', '_debtor'],
    TrustlineRequestEventType: ['_creditor', '_debtor'],
    TrustlineUpdateEventType: ['_creditor', '_debtor'],
    BalanceUpdateEventType: ['_from',  '_to'],
}

standard_event_types = [TransferEventType,
                        CreditlineRequestEventType,
                        CreditlineUpdateEventType,
                        TrustlineRequestEventType,
                        TrustlineUpdateEventType]
