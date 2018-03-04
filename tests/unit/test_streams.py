import pytest

from relay.streams import Client, Subject, DisconnectedError


class TestClient(Client):

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
def client():
    return TestClient()


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
