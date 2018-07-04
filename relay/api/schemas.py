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


class TokenEventSchema(BlockchainEventSchema):
    tokenAddress = Address(attribute='token_address')
    amount = BigInteger(attribute='value')
    from_ = Address(dump_to='from', load_from='from')
    to = Address()


class UserTokenEventSchema(TokenEventSchema):
    direction = fields.Str()
    address = Address(attribute='other_party')


class AccountSummarySchema(Schema):
    class Meta:
        strict = True

    leftGiven = BigInteger(attribute='creditline_left_given')
    leftReceived = BigInteger(attribute='creditline_left_received')
    given = BigInteger(attribute='creditline_given')
    received = BigInteger(attribute='creditline_received')
    balance = BigInteger()


class TrustlineSchema(Schema):
    class Meta:
        strict = True

    leftGiven = BigInteger(attribute='creditline_left_given')
    leftReceived = BigInteger(attribute='creditline_left_received')
    given = BigInteger(attribute='creditline_given')
    received = BigInteger(attribute='creditline_received')
    balance = BigInteger()
    id = fields.Str()
    address = Address(attribute='other_party')


class TxInfosSchema(Schema):
    class Meta:
        strict = True

    balance = BigInteger()
    nonce = fields.Integer()
    gasPrice = BigInteger(attribute='gas_price')
