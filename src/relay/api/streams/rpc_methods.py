from typing import Dict, Iterable

from marshmallow import Schema, ValidationError, fields

from relay.relay import TrustlinesRelay
from relay.streams import Client

from ..fields import Address
from ..schemas import MessageEventSchema
from .rpc_protocol import check_args


class SubscribeSchema(Schema):

    event = fields.String(required=True)
    user = Address(required=True)


@check_args(SubscribeSchema())
def subscribe(trustlines: TrustlinesRelay, client: Client, event: str, user: str):
    if event == "all":
        subscriber = trustlines.subjects[user].subscribe(client)
    else:
        raise ValidationError("Invalid event")
    return subscriber.id


class MessagingSchema(Schema):

    type = fields.String(required=True)
    user = Address(required=True)


@check_args(MessagingSchema())
def messaging_subscribe(
    trustlines: TrustlinesRelay, client: Client, type: str, user: str
):
    if type == "all":
        subscriber = trustlines.messaging[user].subscribe(client)
    else:
        raise ValidationError("Invalid message type")
    return subscriber.id


@check_args(MessagingSchema())
def get_missed_messages(
    trustlines: TrustlinesRelay, client: Client, type: str, user: str
) -> Iterable[Dict]:
    if type == "all":
        messages = MessageEventSchema().dump(
            trustlines.messaging[user].get_missed_messages(), many=True
        )
    else:
        raise ValidationError("Invalid message type")
    return messages
