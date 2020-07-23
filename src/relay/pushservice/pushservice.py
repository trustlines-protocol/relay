import logging
from typing import Optional

import cachetools
import firebase_admin
from firebase_admin import messaging

from relay.blockchain.currency_network_events import (
    TransferEvent,
    TrustlineRequestEvent,
    TrustlineUpdateEvent,
)
from relay.blockchain.events import BlockchainEvent
from relay.events import Event, MessageEvent

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


def dedup_event_id(client_token, event: Event):
    """generate an event id used for deduplicating push notifications

    returns None when a message for the event should be sent anyway, otherwise it
    returns a tuple of the client_token, the event type and the transaction_hash.
    This tuple should be used to deduplicate messages, i.e. we should not send messages twice for
    the same tuple.
    """
    if isinstance(event, BlockchainEvent):
        return client_token, event.type, event.transaction_hash
    else:
        return None


class FirebaseRawPushService:
    """Sends push notifications to firebase. Sending is done based on raw client tokens"""

    def __init__(self, app) -> None:
        """
        Initializes the push service
        Args:
            app: The initialized firebase_admin App
        """

        if not isinstance(app, firebase_admin.App):
            raise Exception("Firebase admin app not initialized")

        self._app = app
        print(self._app)
        self.cache = cachetools.TTLCache(100_000, ttl=3600)

    def send_event(self, client_token, event: Event):
        message = _build_data_message(client_token, event)

        if message is not None:
            msgid = dedup_event_id(client_token, event)
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
            logger.debug(
                "Did not sent push notification for event of type: %s", type(event)
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


def _build_data_message(client_token: str, event: Event) -> Optional[messaging.Message]:
    data = _build_data_prop(event=event)

    if data is not None:
        return messaging.Message(data=data, token=client_token)

    return None


def _build_data_prop(event: Event):
    data = None

    if isinstance(event, TrustlineUpdateEvent):
        data = _get_data_prop_dict(event)
    elif isinstance(event, TransferEvent):
        if event.direction == "received":
            data = _get_data_prop_dict(event)
    elif isinstance(event, TrustlineRequestEvent):
        if event.direction == "received":
            data = _get_data_prop_dict(event)
    elif isinstance(event, MessageEvent):
        if event.type == "PaymentRequest":
            data = {"message": event.message, "eventType": event.type}

    return data


def _get_data_prop_dict(event):
    return {
        "blockHash": str(event.block_hash.hex()),
        "blockNumber": str(event.blocknumber),
        "logIndex": str(event.log_index),
        "transactionHash": str(event.transaction_hash.hex()),
        "eventType": str(event.type),
    }
