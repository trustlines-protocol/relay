from .events import TLNetworkEvent

DepositEventType = 'Deposit'
WithdrawalEventType = 'Withdrawal'
TransferEventType = 'Transfer'
ApprovalEventType = 'Approval'


class UnwEthEvent(TLNetworkEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(web3_event, current_blocknumber, timestamp, from_to_types, user)
        self.token_address = web3_event.get('address')


class ValueEvent(UnwEthEvent):

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


standard_event_types = [TransferEventType,
                        DepositEventType,
                        WithdrawalEventType,
                        ApprovalEventType]
