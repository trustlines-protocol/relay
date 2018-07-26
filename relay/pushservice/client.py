import logging

from relay.streams import Client, DisconnectedError
from relay.events import Event
from relay.logger import get_logger
from .pushservice import FirebaseRawPushService, InvalidClientTokenException


logger = get_logger('pushserviceclient', logging.DEBUG)


class PushNotificationClient(Client):
    """
    Stream Client that sends events as push notification
    """

    def __init__(self, rawPushService: FirebaseRawPushService, client_token: str) -> None:
        super().__init__()
        self._rawPushService = rawPushService
        self.client_token = client_token

    def send(self, id, event):
        if isinstance(event, str) or isinstance(event, dict):
            raise NotImplementedError
        elif not isinstance(event, Event):
            raise ValueError('Unexpected Type: ' + type(event))
        try:
            self._rawPushService.send_event(self.client_token, event)
        except InvalidClientTokenException as e:
            # Token not longer valid means listener is not listing anymore
            raise DisconnectedError from e
        except Exception as e:
            logger.warning('Could not sent push notification to %s\nerror: %s', self.client_token, e)
