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
