import time


class Event(object):

    def __init__(self, timestamp):
        self.timestamp = timestamp


class NetworkValueEvent(Event):

    def __init__(self,
                 network_address,
                 user,
                 value,
                 timestamp=None):
        if timestamp is None:
            timestamp = int(time.time())
        super().__init__(timestamp)
        self.user = user
        self.value = value
        self.network_address = network_address


class NetworkBalanceEvent(NetworkValueEvent):
    type = 'NetworkBalance'


class NetworkAvailableEvent(NetworkValueEvent):
    type = 'NetworkAvailable'
