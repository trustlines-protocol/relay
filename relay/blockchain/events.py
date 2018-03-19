from ..events import Event


class BlockchainEvent(Event):

    def __init__(self, web3_event, current_blocknumber, timestamp):
        super().__init__(timestamp)
        self._web3_event = web3_event
        self.blocknumber = web3_event.get('blockNumber', None)
        self._current_blocknumber = current_blocknumber
        self.transaction_id = web3_event.get('transactionHash')
        self.type = web3_event.get('event')

    @property
    def status(self):
        if self.blocknumber is None:
            return 'sent'
        elif (self._current_blocknumber - self.blocknumber) < 5:
            return 'pending'
        else:
            return 'confirmed'
