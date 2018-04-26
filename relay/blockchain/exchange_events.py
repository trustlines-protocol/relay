from eth_utils import force_bytes
from .events import BlockchainEvent


LogFillEventType = 'LogFill'
LogCancelEventType = 'LogCancel'


class ExchangeEvent(BlockchainEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(web3_event, current_blocknumber, timestamp)
        self.user = user
        self.exchange_address = web3_event.get('address')
        self.order_hash = force_bytes(web3_event.get('args').get('orderHash'))
        self.maker_token = web3_event.get('args').get('makerToken')
        self.taker_token = web3_event.get('args').get('takerToken')

    @property
    def from_(self):
        return self._web3_event.get('args')[from_to_types[self._web3_event.get('event')][0]]


class LogFillEvent(ExchangeEvent):

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

    @property
    def filled_maker_amount(self):
        return self._web3_event.get('args').get('filledMakerTokenAmount')

    @property
    def filled_taker_amount(self):
        return self._web3_event.get('args').get('filledTakerTokenAmount')


class LogCancelEvent(ExchangeEvent):

    @property
    def cancelled_maker_amount(self):
        return self._web3_event.get('args').get('cancelledMakerTokenAmount')

    @property
    def cancelled_taker_amount(self):
        return self._web3_event.get('args').get('cancelledTakerTokenAmount')


event_builders = {
    LogFillEventType: LogFillEvent,
    LogCancelEventType: LogCancelEvent
}


from_to_types = {
    LogFillEventType: ['maker', 'taker'],
    LogCancelEventType: ['maker']
}
