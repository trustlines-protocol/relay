import random
import logging

from .logger import get_logger

logger = get_logger('streams', logging.DEBUG)


class Client():

    def send(self, id, event):
        raise NotImplementedError


class DisconnectedError(Exception):
    pass


class Subject():

    def __init__(self):
        self.subscriptions = []

    def subscribe(self, client):
        logger.debug('New Subscription')
        subscription = Subscription(client, self._create_id(), self)
        self.subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription):
        logger.debug('Unsubscription')
        self.subscriptions.remove(subscription)

    def publish(self, event):
        logger.debug('Sent event to {} subscribers'.format(len(self.subscriptions)))
        for subscription in self.subscriptions:
            subscription.notify(event)

    @staticmethod
    def _create_id():
        return '0x{:016X}'.format(random.randint(0, 16**16-1))


class Subscription():
    def __init__(self, client, id, subject):
        self.client = client
        self.id = id
        self.subject = subject
        self.closed = False

    def notify(self, event):
        if not self.closed:
            try:
                self.client.send(self.id, event)
            except DisconnectedError:
                self.unsubscribe()

    def unsubscribe(self):
        self.closed = True
        self.subject.unsubscribe(self)
