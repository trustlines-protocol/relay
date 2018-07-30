import random
import logging
from typing import Union, List

from .blockchain.events import Event
from .logger import get_logger

logger = get_logger('streams', logging.DEBUG)


Publishable = Union[str, dict, Event]


class Client(object):

    def send(self, id: str, event: Publishable):
        raise NotImplementedError


class DisconnectedError(Exception):
    pass


class Subject(object):

    def __init__(self) -> None:
        self.subscriptions: List[Subscription] = []

    def subscribe(self, client: Client) -> 'Subscription':
        logger.debug('New Subscription')
        subscription = Subscription(client, self._create_id(), self)
        self.subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription: 'Subscription') -> None:
        logger.debug('Unsubscription')
        self.subscriptions.remove(subscription)

    def publish(self, event: Publishable):
        if self.subscriptions:
            logger.debug('Sent event to {} subscribers'.format(len(self.subscriptions)))
        result = 0
        # The call to notify in the following code is allowed to unsubscribe
        # the client. That means we need to copy the self.subscriptions list as
        # it's being modified when unsubscribing.
        for subscription in self.subscriptions[:]:
            if subscription.notify(event):
                result += 1
        return result

    @staticmethod
    def _create_id() -> str:
        return '0x{:016X}'.format(random.randint(0, 16**16-1))


class Subscription():
    def __init__(self, client: Client, id: str, subject: Subject) -> None:
        self.client = client
        self.id = id
        self.subject = subject
        self.closed = False

    def notify(self, event: Publishable) -> bool:
        if not self.closed:
            try:
                self.client.send(self.id, event)
                return True
            except DisconnectedError:
                self.unsubscribe()

        return False

    def unsubscribe(self) -> None:
        if not self.closed:
            self.closed = True
            self.subject.unsubscribe(self)


class MessagingSubject(Subject):

    def __init__(self):
        super().__init__()
        self.events: List[Publishable] = []

    def get_missed_messages(self):
        events = self.events
        self.events = []
        return events

    def publish(self, event: Publishable):
        result = super().publish(event)
        if result == 0:
            self.events.append(event)
        return result
