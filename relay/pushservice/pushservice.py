import json
import logging
from typing import Optional

import firebase_admin
from firebase_admin import credentials, messaging

from relay.events import Event, MessageEvent, AccountEvent
from relay.blockchain.events import TLNetworkEvent
from relay.blockchain.currency_network_events import TransferEvent, TrustlineRequestEvent, TrustlineUpdateEvent
from relay.api.schemas import UserCurrencyNetworkEventSchema, MessageEventSchema
from .client_token_db import ClientTokenDB
from relay.logger import get_logger


logger = get_logger('pushservice', logging.DEBUG)


# see https://firebase.google.com/docs/cloud-messaging/admin/errors
INVALID_CLIENT_TOKEN_ERRORS = [
    'invalid-registration-token',
    'registration-token-not-registered',
    'invalid-argument',
]


class PushServiceException(Exception):
    pass


class InvalidClientTokenException(PushServiceException):
    pass


class MessageNotSentException(PushServiceException):
    pass


class FirebaseRawPushService:
    """Sends push notifications to firebase. Sending is done based on raw client tokens"""

    def __init__(self, path_to_keyfile: str) -> None:
        """
        Initializes the push service
        Args:
            path_to_keyfile: Path to json keyfile with firebase credentials
        """
        cred = credentials.Certificate(path_to_keyfile)
        self._app = firebase_admin.initialize_app(cred)

    def send_event(self, client_token, event: Event):
        message = _build_event_message(client_token, event)
        if message is not None:
            try:
                messaging.send(message, app=self._app)
            except messaging.ApiCallError as e:
                # Check if error code is because token is invalid
                # see https://firebase.google.com/docs/cloud-messaging/admin/errors
                if e.code in INVALID_CLIENT_TOKEN_ERRORS:
                    raise InvalidClientTokenException from e
                else:
                    raise MessageNotSentException from e
        else:
            logger.warning('Could not sent event of type: %s', type(event))

    def check_client_token(self, client_token: str) -> bool:
        """
        Check if the client_token is valid by sending a test message with the dry_run flag being set
        Args:
            client_token: The client token to check

        Returns: True if the client token is valid, false otherwise

        """
        test_message = messaging.Message(
            token=client_token
        )
        try:
            messaging.send(test_message, app=self._app, dry_run=True)  # dry run to test token
        except ValueError:
            return False
        except messaging.ApiCallError as e:
            # Check if error code is because token is invalid
            # see https://firebase.google.com/docs/cloud-messaging/admin/errors
            if e.code in INVALID_CLIENT_TOKEN_ERRORS:
                return False
            else:
                raise
        return True


def _build_event_message(client_token: str, event: Event) -> Optional[messaging.Message]:
    if isinstance(event, TLNetworkEvent) or isinstance(event, AccountEvent):
        data = UserCurrencyNetworkEventSchema().dump(event).data
    elif isinstance(event, MessageEvent):
        data = MessageEventSchema().dump(event).data
    else:
        return None

    message = messaging.Message(
        notification=_build_notification(event),
        data={
            'event': json.dumps(data),
        },
        token=client_token,
    )

    return message


def _build_notification(event: Event) -> messaging.Notification:
    notification = None
    if isinstance(event, TransferEvent):
        if event.direction == 'received':
            notification = messaging.Notification(
                title='Payment received',
                body='Click for more details',
            )
    elif isinstance(event, TrustlineRequestEvent):
        if event.direction == 'received':
            notification = messaging.Notification(
                title='Trustline Update Request',
                body='Someone wants to update a trustline',
            )
    elif isinstance(event, TrustlineUpdateEvent):
        notification = messaging.Notification(
            title='Trustline Update',
            body='A trustline was updated',
        )
    elif isinstance(event, MessageEvent):
        if event.type == 'PaymentRequest':
            notification = messaging.Notification(
                title='Payment Request',
                body='Click for more details',
            )

    return notification


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
        # Iterate over copy list, because we might delete from this list
        for client_token in list(self._client_token_db.get_client_tokens(user_address)):
            try:
                self._firebaseRawPushService.send_event(client_token, event)
            except InvalidClientTokenException:
                self._client_token_db.delete_client_token(user_address, client_token)
