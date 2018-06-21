from relay.streams import Client
from relay.events import Event
from .pushservice import FirebaseRawPushService


class FirebaseClient(Client):

    def __init__(self, firebaseRawPushService: FirebaseRawPushService, client_token: str) -> None:
        self._firebaseRawPushService = firebaseRawPushService
        self.client_token = client_token

    def send(self, id, event):
        if isinstance(event, str) or isinstance(event, dict):
            raise NotImplementedError
        elif not isinstance(event, Event):
            raise ValueError('Unexpected Type: ' + type(event))
        self._firebaseRawPushService.send_event(self.client_token, event)
