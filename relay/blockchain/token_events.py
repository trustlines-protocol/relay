from .events import TLNetworkEvent

TransferEventType = 'Transfer'
ApprovalEventType = 'Approval'


class TokenEvent(TLNetworkEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(web3_event, current_blocknumber, timestamp, from_to_types, user)
        self.token_address = web3_event.get('address')


class ValueEvent(TokenEvent):

    @property
    def value(self):
        return self._web3_event.get('args').get('_value')


class TransferEvent(ValueEvent):
    pass


class ApprovalEvent(ValueEvent):
    pass


event_builders = {
    TransferEventType: TransferEvent,
    ApprovalEventType: ApprovalEvent
}


from_to_types = {
    TransferEventType: ['_from', '_to'],
    ApprovalEventType: ['_owner', '_spender']
}


standard_event_types = [TransferEventType,
                        ApprovalEventType]
