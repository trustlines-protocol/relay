from eth_utils import force_bytes, is_hex, decode_hex
from .events import TLNetworkEvent, BlockchainEvent  # NOQA

LogFillEventType = 'LogFill'
LogCancelEventType = 'LogCancel'


class ExchangeEvent(TLNetworkEvent):

    def __init__(self, web3_event, current_blocknumber, timestamp, user=None):
        super().__init__(web3_event, current_blocknumber, timestamp, from_to_types, user)
        self.exchange_address = web3_event.get('address')
        # NOTE: The argument orderHash can be a hex string because the indexer currently can
        #       not save bytes in the database. See issue https://github.com/trustlines-network/py-eth-index/issues/16
        if (is_hex(web3_event.get('args').get('orderHash'))):
            self.order_hash = decode_hex(web3_event.get('args').get('orderHash'))
        else:
            self.order_hash = force_bytes(web3_event.get('args').get('orderHash'))
        self.maker_token = web3_event.get('args').get('makerToken')
        self.taker_token = web3_event.get('args').get('takerToken')


class LogFillEvent(ExchangeEvent):

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
    LogCancelEventType: ['maker', 'maker']
}


standard_event_types = [LogFillEventType, LogCancelEventType]
