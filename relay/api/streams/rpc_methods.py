from marshmallow import fields, Schema, ValidationError

from .rpc_protocol import check_args
from ..fields import Address

from relay.main import TrustlinesRelay
from relay.streams import Client


class SubscribeSchema(Schema):
    class Meta:
        strict = True
    event = fields.String(required=True)
    user = Address(required=True)


@check_args(SubscribeSchema())
def subscribe(trustlines: TrustlinesRelay, client: Client, event: str, user: str):
    if event == 'all':
        subscriber = trustlines.subjects[user].subscribe(client)
    else:
        raise ValidationError('Invalid event')
    return subscriber.id


class MessagingSchema(Schema):
    class Meta:
        strict = True
    type = fields.String(required=True)
    user = Address(required=True)


@check_args(MessagingSchema())
def messaging_subscribe(trustlines: TrustlinesRelay, client: Client, type: str, user: str):
    if type == 'all':
        subscriber = trustlines.messaging[user].subscribe(client)
    else:
        raise ValidationError('Invalid message type')
    return subscriber.id


@check_args(MessagingSchema())
def get_missed_messages(trustlines: TrustlinesRelay, client: Client, type: str, user: str):
    if type == 'all':
        messages = trustlines.messaging[user].get_missed_messages()
    else:
        raise ValidationError('Invalid message type')
    return messages
