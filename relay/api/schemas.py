from marshmallow import Schema, fields

from .fields import Address, BigInteger


class EventSchema(Schema):
    class Meta:
        strict = True
    timestamp = fields.Integer()


class BlockchainEventSchema(EventSchema):
    blockNumber = fields.Integer(attribute='blocknumber')
    type = fields.Str(default='event')
    transactionId = fields.Str(attribute='transaction_id')
    status = fields.Str()


class CurrencyNetworkEventSchema(BlockchainEventSchema):
    networkAddress = Address(attribute='network_address')
    amount = BigInteger(attribute='value')
    given = BigInteger()
    received = BigInteger()
    balance = BigInteger()
    leftGiven = BigInteger(attribute='left_given')
    leftReceived = BigInteger(attribute='left_received')
    from_ = Address(dump_to='from', load_from='from')
    to = Address()


class UserCurrencyNetworkEventSchema(CurrencyNetworkEventSchema):
    direction = fields.Str()
    address = Address(attribute='other_party')
