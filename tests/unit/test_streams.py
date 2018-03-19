import pytest

from relay.streams import Client, Subject, MessagingSubject, DisconnectedError


class LogClient(Client):

    def __init__(self):
        self.events = []

    def send(self, id, event):
        if event == 'disconnect':
            raise DisconnectedError
        self.events.append((id, event))


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
    subscribtion = subject.subscribe(client)
    subject.publish(event='test')
    id = subscribtion.id
    assert client.events == [(id, 'test')]
    assert not subscribtion.closed
    assert len(subject.subscriptions) == 1


def test_cancel_subscription(subject, client):
    subscribtion = subject.subscribe(client)
    subscribtion.unsubscribe()
    subject.publish(event='test')
    assert client.events == []
    assert subscribtion.closed
    assert len(subject.subscriptions) == 0


def test_auto_unsubscribe(subject, client):
    subscribtion = subject.subscribe(client)
    subject.publish(event='disconnect')  # throws disconnected error, should unsubscribe
    subject.publish(event='test')
    assert client.events == []
    assert subscribtion.closed
    assert len(subject.subscriptions) == 0


def test_subscription_after_puplish(messaging_subject, client):
    assert not messaging_subject.publish(event='test')
    subscribtion = messaging_subject.subscribe(client)
    assert messaging_subject.get_missed_messages() == ['test']
    assert not subscribtion.closed


def test_subscription_after_resubscribe(messaging_subject, client):
    messaging_subject.publish(event='test')
    subscribtion = messaging_subject.subscribe(client)
    messaging_subject.get_missed_messages()
    subscribtion.unsubscribe()
    client.events.clear()
    messaging_subject.subscribe(client)
    assert messaging_subject.get_missed_messages() == []
    assert client.events == []


def test_subscription_both(messaging_subject, client):
    assert not messaging_subject.publish(event='test1')
    subscribtion = messaging_subject.subscribe(client)
    assert messaging_subject.publish(event='test2')
    id = subscribtion.id
    assert messaging_subject.get_missed_messages() == ['test1']
    assert client.events == [(id, 'test2')]
    assert not subscribtion.closed
