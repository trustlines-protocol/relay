from .events import BlockchainEvent

DepositEventType = 'Deposit'
WithdrawalEventType = 'Withdrawal'
TransferEventType = 'Transfer'
ApprovalEventType = 'Approval'


class TokenEvent(BlockchainEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(web3_event, current_blocknumber, timestamp)
        self.user = user
        self.token_address = web3_event.get('address')

    @property
    def from_(self):
        return self._web3_event.get('args')[from_to_types[self._web3_event.get('event')][0]]

    @property
    def to(self):
        return self._web3_event.get('args')[from_to_types[self._web3_event.get('event')][1]]

    @property
    def direction(self):
        if self.user is None:
            return None
        if self.from_ == self.user:
            return 'sent'
        else:
            return 'received'

    @property
    def other_party(self):
        if self.user is None:
            return None
        if self.from_ == self.user:
            return self.to
        else:
            return self.from_


class ValueEvent(TokenEvent):

    @property
    def value(self):
        return self._web3_event.get('args').get('wad')


class TransferEvent(ValueEvent):
    pass


class DepositEvent(ValueEvent):
    pass


class WithdrawalEvent(ValueEvent):
    pass


class ApprovalEvent(ValueEvent):
    pass


event_builders = {
    TransferEventType: TransferEvent,
    DepositEventType: DepositEvent,
    WithdrawalEventType: WithdrawalEvent,
    ApprovalEventType: ApprovalEvent
}


from_to_types = {
    TransferEventType: ['src', 'dst'],
    DepositEventType: ['dst', 'dst'],
    WithdrawalEventType: ['src', 'src'],
    ApprovalEventType: ['src', 'guy']
}
