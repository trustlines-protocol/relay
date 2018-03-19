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
        if self.subscriptions:
            logger.debug('Sent event to {} subscribers'.format(len(self.subscriptions)))
        result = 0
        for subscription in self.subscriptions:
            if subscription.notify(event):
                result += 1
        return result

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
                return True
            except DisconnectedError:
                self.unsubscribe()

        return False

    def unsubscribe(self):
        self.closed = True
        self.subject.unsubscribe(self)


class MessagingSubject(Subject):

    def __init__(self):
        super().__init__()
        self.events = []

    def get_missed_messages(self):
        events = self.events
        self.events = []
        return events

    def publish(self, event):
        result = super().publish(event)
        if result == 0:
            self.events.append(event)
        return result
