import pytest
import gevent

from relay.streams import Client, Subject, MessagingSubject, DisconnectedError, Subscription, Publishable


class LogClient(Client):

    def __init__(self):
        super().__init__()
        self.events = []

    def _execute_send(self, subscription: Subscription, event: Publishable) -> None:
        if event == 'disconnect':
            raise DisconnectedError
        self.events.append((subscription.id, event))


class SafeLogClient(Client):
    "this client does not raise DisconnectedError"
    def __init__(self):
        super().__init__()
        self.events = []

    def _execute_send(self, subscription: Subscription, event: Publishable) -> None:
        self.events.append((subscription.id, event))


class GeventClient(Client):

    def _execute_send(self, subscription: Subscription, event: Publishable) -> None:
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
    subject.publish(event='test')
    id = subscription.id
    assert client.events == [(id, 'test')]
    assert not subscription.closed
    assert len(subject.subscriptions) == 1


def test_cancel_subscription(subject, client):
    subscription = subject.subscribe(client)
    subscription.unsubscribe()
    subject.publish(event='test')
    assert client.events == []
    assert subscription.closed
    assert len(subject.subscriptions) == 0


def test_auto_unsubscribe(subject, client):
    subscription = subject.subscribe(client)
    subject.publish(event='disconnect')  # throws disconnected error, should unsubscribe
    subject.publish(event='test')
    assert client.events == []
    assert subscription.closed
    assert len(subject.subscriptions) == 0


def test_auto_unsubscribe_dont_skip(subject):
    """test that publishing also works when auto-unsubscribing
    see https://github.com/trustlines-network/relay/issues/85"""
    clients = [LogClient(), SafeLogClient()]
    for c in clients:
        subject.subscribe(c)
    subject.publish(event='disconnect')  # the first one throws and get's auto-unsubscribed
    assert clients[1].events, "second client not notified"


def test_subscription_after_puplish(messaging_subject, client):
    assert not messaging_subject.publish(event='test')
    subscription = messaging_subject.subscribe(client)
    assert messaging_subject.get_missed_messages() == ['test']
    assert not subscription.closed


def test_subscription_after_resubscribe(messaging_subject, client):
    messaging_subject.publish(event='test')
    subscription = messaging_subject.subscribe(client)
    messaging_subject.get_missed_messages()
    subscription.unsubscribe()
    client.events.clear()
    messaging_subject.subscribe(client)
    assert messaging_subject.get_missed_messages() == []
    assert client.events == []


def test_subscription_both(messaging_subject, client):
    assert not messaging_subject.publish(event='test1')
    subscription = messaging_subject.subscribe(client)
    assert messaging_subject.publish(event='test2')
    id = subscription.id
    assert messaging_subject.get_missed_messages() == ['test1']
    assert client.events == [(id, 'test2')]
    assert not subscription.closed


def test_unsubscription_race_condition(subject):
    """Tests for race condition when client can unschedule greenlet and thus delay unsubscription"""
    client1 = GeventClient()
    subject.subscribe(client1)
    # publish will unsubscribe because client is disconnected. Because it is delayed it will try to unsubscribe twice
    gevent.joinall((gevent.spawn(subject.publish, 'test1'), gevent.spawn(subject.publish, 'test2')), raise_error=True)
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
