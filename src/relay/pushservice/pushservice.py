import json
import logging
from typing import Optional

import cachetools
import firebase_admin
from firebase_admin import credentials, messaging

from relay.api.schemas import MessageEventSchema, UserCurrencyNetworkEventSchema
from relay.blockchain.currency_network_events import (
    TransferEvent,
    TrustlineRequestEvent,
    TrustlineUpdateEvent,
)
from relay.blockchain.events import TLNetworkEvent
from relay.events import AccountEvent, Event, MessageEvent

logger = logging.getLogger("pushservice")


# see https://firebase.google.com/docs/cloud-messaging/admin/errors
INVALID_CLIENT_TOKEN_ERRORS = [
    "invalid-registration-token",
    "registration-token-not-registered",
    "invalid-argument",
    "mismatched-credential",
]


class PushServiceException(Exception):
    pass


class InvalidClientTokenException(PushServiceException):
    pass


class MessageNotSentException(PushServiceException):
    pass


def dedup_message_id(client_token, message):
    """generate a message id used for deduplicating push notifications

    returns None when the message should be sent anyway, otherwise it
    returns a tuple of the client_token, the message title, the
    message body and the transaction_id. This tuple should be used to
    deduplicate messages, i.e. we should not send messages twice for
    the same tuple.
    """
    if message is None or message.notification is None:
        return None
    event_data = json.loads(message.data["event"])
    transaction_id = event_data.get("transactionId")
    if not transaction_id:
        return None

    return (
        client_token,
        message.notification.title,
        message.notification.body,
        transaction_id,
    )


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
        self.cache = cachetools.TTLCache(100_000, ttl=3600)

    def send_event(self, client_token, event: Event):
        message = _build_event_message(client_token, event)
        if message is not None:
            msgid = dedup_message_id(client_token, message)
            if msgid is not None and msgid in self.cache:
                logger.debug("not sending duplicate message for event %s", event)
                return
            try:
                messaging.send(message, app=self._app)
                if msgid is not None:
                    self.cache[msgid] = True
            except messaging.ApiCallError as e:
                # Check if error code is because token is invalid
                # see https://firebase.google.com/docs/cloud-messaging/admin/errors
                if e.code in INVALID_CLIENT_TOKEN_ERRORS:
                    raise InvalidClientTokenException from e
                else:
                    raise MessageNotSentException(
                        f"Message could not be sent: {e.code}"
                    ) from e
        else:
            logger.warning(
                "Could not sent push notification for event of type: %s", type(event)
            )

    def check_client_token(self, client_token: str) -> bool:
        """
        Check if the client_token is valid by sending a test message with the dry_run flag being set
        Args:
            client_token: The client token to check

        Returns: True if the client token is valid, false otherwise

        """
        test_message = messaging.Message(token=client_token)
        try:
            messaging.send(
                test_message, app=self._app, dry_run=True
            )  # dry run to test token
        except ValueError:
            return False
        except messaging.ApiCallError as e:
            # Check if error code is because token is invalid
            # see https://firebase.google.com/docs/cloud-messaging/admin/errors
            if e.code in INVALID_CLIENT_TOKEN_ERRORS:
                logger.debug(f"Invalid client token {client_token}: {e.code}")
                return False
            else:
                raise
        return True


def _build_event_message(
    client_token: str, event: Event
) -> Optional[messaging.Message]:
    if isinstance(event, TLNetworkEvent) or isinstance(event, AccountEvent):
        data = UserCurrencyNetworkEventSchema().dump(event)
    elif isinstance(event, MessageEvent):
        data = MessageEventSchema().dump(event)
    else:
        return None

    message = messaging.Message(
        notification=_build_notification(event),
        data={"event": json.dumps(data)},
        token=client_token,
    )

    return message


def _build_notification(event: Event) -> messaging.Notification:
    notification = None
    if isinstance(event, TransferEvent):
        if event.direction == "received":
            notification = messaging.Notification(
                title="Payment received", body="Click for more details"
            )
    elif isinstance(event, TrustlineRequestEvent):
        if event.direction == "received":
            notification = messaging.Notification(
                title="Trustline Update Request",
                body="Someone wants to update a trustline",
            )
    elif isinstance(event, TrustlineUpdateEvent):
        notification = messaging.Notification(
            title="Trustline Update", body="A trustline was updated"
        )
    elif isinstance(event, MessageEvent):
        if event.type == "PaymentRequest":
            notification = messaging.Notification(
                title="Payment Request", body="Click for more details"
            )

    return notification
