import logging
import random
from typing import Iterable, List  # noqa: F401

from .events import Event, MessageEvent

logger = logging.getLogger("streams")


class Client(object):
    """Represents the connection to a client. Different subscriptions can be connected to the same client"""

    def __init__(self) -> None:
        self.subscriptions: List[Subscription] = []
        self.closed = False

    def register(self, subscription: "Subscription") -> None:
        """
        Registers a subscription that this client has done.
        On closing the connection with `close` these subscription will get unsubscribed
        """
        self.subscriptions.append(subscription)

    def unregister(self, subscription: "Subscription") -> None:
        """
        Unregisters a subscription that this client is not listing for anymore.
        On closing the connection with `close` these subscription will get unsubscribed
        """
        self.subscriptions.remove(subscription)

    def send(self, subscription: "Subscription", event: Event) -> None:
        """
        Sends an event to the client that belongs to a subscription with the given subscription id
        Raises:
            DisconnectedError: This is raised if the client has already disconnected.
        """
        if subscription not in self.subscriptions:
            raise ValueError("Unknown subscription")
        if self.closed:
            raise RuntimeError("Client connection is closed")
        self._execute_send(subscription, event)

    def _execute_send(self, subscription: "Subscription", event: Event) -> None:
        """
        Executes the sending
        Should be implemented by sub class
        may raise DisconnectedError
        """
        raise NotImplementedError

    def close(self) -> None:
        """
        Should be called when the connection to this client is closed.
        This will unsubscribe all registered subscriptions
        """
        if not self.closed:
            self.closed = True
            for subscription in self.subscriptions[
                :
            ]:  # copy, because we are deleting from that list
                subscription.unsubscribe()
            assert len(self.subscriptions) == 0


class DisconnectedError(Exception):
    pass


class Subject(object):
    """
    A subject that clients can subscribe to to get notifications
    """

    def __init__(self) -> None:
        self.subscriptions: List[Subscription] = []

    def subscribe(self, client: Client) -> "Subscription":
        """
        Subscribe to the topic to get notified about updates
        Args:
            client: the client that wants to subscribe

        Returns: The subscription. Can be used to cancel these updates

        """
        logger.debug("New Subscription")
        subscription = Subscription(client, id=self._create_id(), subject=self)
        self.subscriptions.append(subscription)
        return subscription

    def unsubscribe(self, subscription: "Subscription") -> None:
        logger.debug("Unsubscription")
        self.subscriptions.remove(subscription)

    def publish(self, event: Event):
        assert isinstance(event, Event)
        if self.subscriptions:
            logger.debug("Sent event to {} subscribers".format(len(self.subscriptions)))
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
        return "0x{:016X}".format(random.randint(0, 16 ** 16 - 1))


class Subscription:
    def __init__(self, client: Client, *, id: str, subject: Subject) -> None:
        self.client = client
        self.id = id
        self.subject = subject
        self.closed = False
        self.client.register(self)

    def notify(self, event: Event) -> bool:
        assert isinstance(event, Event)
        if not self.closed:
            try:
                self.client.send(self, event)
                return True
            except DisconnectedError:
                self.unsubscribe()

        return False

    def unsubscribe(self) -> None:
        if not self.closed:
            self.closed = True
            self.subject.unsubscribe(self)
            self.client.unregister(self)


class MessagingSubject(Subject):
    def __init__(self):
        super().__init__()
        self.events: List[MessageEvent] = []

    def subscribe(self, client: Client, *, silent=False) -> "MessagingSubscription":
        """
        Subscribe to the topic to get notified about updates
        Args:
            client: the client that wants to subscribe
            silent: whether this subscription should mark messages as read

        Returns: The subscription. Can be used to cancel these updates

        """
        logger.debug("New MessagingSubscription")
        subscription = MessagingSubscription(
            client, id=self._create_id(), subject=self, silent=silent
        )
        self.subscriptions.append(subscription)
        return subscription

    def get_missed_messages(self) -> Iterable[MessageEvent]:
        events = self.events
        self.events = []
        return events

    def publish(self, event: Event) -> int:
        logger.debug("Publish Message")
        if not isinstance(event, MessageEvent):
            raise RuntimeError("Can only send MessageEvent over message subject")
        if self.subscriptions:
            logger.debug(
                "Sent message to {} subscribers".format(len(self.subscriptions))
            )
        read_by = 0
        # The call to notify in the following code is allowed to unsubscribe
        # the client. That means we need to copy the self.subscriptions list as
        # it's being modified when unsubscribing.
        for subscription in self.subscriptions[:]:
            if isinstance(subscription, MessagingSubscription):
                successfully = subscription.notify(event)
                if successfully and not subscription.silent:
                    read_by += 1
            else:
                raise RuntimeError("Unexpected Subscription")
        if not read_by:
            self.events.append(event)
        return read_by


class MessagingSubscription(Subscription):
    def __init__(
        self, client: Client, *, id: str, subject: Subject, silent=False
    ) -> None:
        super().__init__(client, id=id, subject=subject)
        self.silent = silent
