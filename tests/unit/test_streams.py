from collections import namedtuple

import pytest
import gevent

from relay.streams import Client, Subject, MessagingSubject, DisconnectedError, Subscription, Event
from relay.events import MessageEvent


IdEventTuple = namedtuple('IdEventTuple', 'id, event')


class LogClient(Client):

    def __init__(self):
        super().__init__()
        self.events = []

    def _execute_send(self, subscription: Subscription, event: Event) -> None:
        if isinstance(event, MessageEvent) and event.message == 'disconnect':
                raise DisconnectedError
        self.events.append(IdEventTuple(subscription.id, event))


class SafeLogClient(Client):
    "this client does not raise DisconnectedError"
    def __init__(self):
        super().__init__()
        self.events = []

    def _execute_send(self, subscription: Subscription, event: Event) -> None:
        self.events.append(IdEventTuple(subscription.id, event))


class GeventClient(Client):

    def _execute_send(self, subscription: Subscription, event: Event) -> None:
        gevent.sleep(0.1)
        raise DisconnectedError


@pytest.fixture()
def subject():
    return Subject()


@pytest.fixture()
def messaging_subject():
    return MessagingSubject()


@pytest.fixture()
def client():
    return LogClient()


def test_subscription(subject, client):
    subscription = subject.subscribe(client)
    subject.publish(event=MessageEvent('test'))
    id = subscription.id
    item = client.events[0]
    assert item.id == id
    assert item.event.message == 'test'
    assert not subscription.closed
    assert len(subject.subscriptions) == 1


def test_cancel_subscription(subject, client):
    subscription = subject.subscribe(client)
    subscription.unsubscribe()
    subject.publish(event=MessageEvent('test'))
    assert client.events == []
    assert subscription.closed
    assert len(subject.subscriptions) == 0


def test_auto_unsubscribe(subject, client):
    subscription = subject.subscribe(client)
    subject.publish(event=MessageEvent('disconnect'))  # throws disconnected error, should unsubscribe
    subject.publish(event=MessageEvent('test'))
    assert client.events == []
    assert subscription.closed
    assert len(subject.subscriptions) == 0


def test_auto_unsubscribe_dont_skip(subject):
    """test that publishing also works when auto-unsubscribing
    see https://github.com/trustlines-network/relay/issues/85"""
    clients = [LogClient(), SafeLogClient()]
    for c in clients:
        subject.subscribe(c)
    subject.publish(event=MessageEvent('disconnect'))  # the first one throws and get's auto-unsubscribed
    assert clients[1].events, "second client not notified"


def test_subscription_after_puplish(messaging_subject, client):
    assert not messaging_subject.publish(event=MessageEvent('test'))
    subscription = messaging_subject.subscribe(client)
    missed_messages = messaging_subject.get_missed_messages()
    assert len(missed_messages) == 1
    assert missed_messages[0].message == 'test'
    assert not subscription.closed


def test_subscription_after_resubscribe(messaging_subject, client):
    messaging_subject.publish(event=MessageEvent('test'))
    subscription = messaging_subject.subscribe(client)
    messaging_subject.get_missed_messages()
    subscription.unsubscribe()
    client.events.clear()
    messaging_subject.subscribe(client)
    assert messaging_subject.get_missed_messages() == []
    assert client.events == []


def test_subscription_both(messaging_subject, client):
    assert not messaging_subject.publish(event=MessageEvent('test1'))
    subscription = messaging_subject.subscribe(client)
    assert messaging_subject.publish(event=MessageEvent('test2'))
    id = subscription.id
    missed_messages = messaging_subject.get_missed_messages()
    assert len(missed_messages) == 1
    assert missed_messages[0].message == 'test1'
    item = client.events[0]
    assert item.id == id
    assert item.event.message == 'test2'
    assert not subscription.closed


def test_unsubscription_race_condition(subject):
    """Tests for race condition when client can unschedule greenlet and thus delay unsubscription"""
    client1 = GeventClient()
    subject.subscribe(client1)
    # publish will unsubscribe because client is disconnected. Because it is delayed it will try to unsubscribe twice
    gevent.joinall(
        (gevent.spawn(subject.publish, MessageEvent('test1')), gevent.spawn(subject.publish, MessageEvent('test2'))),
        raise_error=True)
    assert subject.subscriptions == []


def test_many_subscription(subject):
    client = SafeLogClient()
    subject.subscribe(client)
    subject.subscribe(client)
    assert len(client.subscriptions) == 2


def test_stop_subscription(subject):
    client = SafeLogClient()
    subscription1 = subject.subscribe(client)
    subject.subscribe(client)
    subscription1.unsubscribe()
    assert len(client.subscriptions) == 1


def test_close_client(subject):
    client = SafeLogClient()
    subscription1 = subject.subscribe(client)
    subscription2 = subject.subscribe(client)
    client.close()
    assert client.closed
    assert len(client.subscriptions) == 0
    assert subscription1.closed
    assert subscription2.closed
