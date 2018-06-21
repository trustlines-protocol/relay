import json

import firebase_admin
from firebase_admin import credentials
from firebase_admin import messaging

from relay.events import Event
from relay.api.schemas import UserCurrencyNetworkEventSchema
from .client_token_db import ClientTokenDB


class FirebaseRawPushService:
    """Sends push notifications to firebase. Sending is done based on raw client tokens"""

    def __init__(self) -> None:
        self._app = None

    def initialize(self, path_to_keyfile: str) -> None:
        """
        Initializes the push service
        Args:
            path_to_keyfile: Path to json keyfile with firebase credentials
        """
        cred = credentials.Certificate(path_to_keyfile)
        self.app = firebase_admin.initialize_app(cred)

    def send_event(self, client_token, event: Event):
        message = self._build_event_message(client_token, event)
        messaging.send(message, app=self._app)

    def _build_event_message(self, client_token: str, event: Event) -> messaging.Message:
        data = UserCurrencyNetworkEventSchema().dump(event).data
        event_type = event.type

        message = messaging.Message(
            notification=messaging.Notification(
                title='New {}'.format(event_type),
                body='Click for more details',
            ),
            data={
                'event': json.dumps(data),
            },
            token=client_token,
        )

        return message


class FirebasePushService:
    """Sends push notifications to firebase. Sending is done based on ethereum addresses"""

    def __init__(self, client_token_db: ClientTokenDB, firebaseRawPushService: FirebaseRawPushService) -> None:
        """
        Args:
            client_token_db: Database to map ethereum address to client token
            firebaseRawPushService: Initialized firebase service to send push notifications
        """
        self._firebaseRawPushService = firebaseRawPushService
        self._client_token_db = client_token_db

    def send_event(self, user_address: str, event: Event) -> None:
        """
        Sends an event to a user. The client to push the notification to is taken from the database
        """
        for client_token in self._client_token_db.get_client_tokens(user_address):
            self._firebaseRawPushService.send_event(client_token, event)
