from marshmallow import fields, Schema, ValidationError

from .rpc_protocol import check_args
from ..fields import Address


class SubscribeSchema(Schema):
    class Meta:
        strict = True
    event = fields.String(required=True)
    user = Address(required=True)


@check_args(SubscribeSchema())
def subscribe(trustlines, client, event, user):
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
def messaging_subscribe(trustlines, client, type, user):
    if type == 'all':
        subscriber = trustlines.messaging[user].subscribe(client)
    else:
        raise ValidationError('Invalid message type')
    return subscriber.id


@check_args(MessagingSchema())
def get_missed_messages(trustlines, client, type, user):
    if type == 'all':
        messages = trustlines.messaging[user].get_missed_messages()
    else:
        raise ValidationError('Invalid message type')
    return messages
