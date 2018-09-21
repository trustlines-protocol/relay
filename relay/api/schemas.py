from marshmallow import Schema, fields

from .fields import Address, BigInteger, HexBytes


class EventSchema(Schema):
    class Meta:
        strict = True
    timestamp = fields.Integer()


class MessageEventSchema(EventSchema):
    message = fields.Str()


class BlockchainEventSchema(EventSchema):
    blockNumber = fields.Integer(attribute='blocknumber')
    type = fields.Str(default='event')
    transactionId = HexBytes(attribute='transaction_id')
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
    counterParty = Address(attribute='counter_party')
    user = Address()


class TokenEventSchema(BlockchainEventSchema):
    tokenAddress = Address(attribute='token_address')
    amount = BigInteger(attribute='value')
    from_ = Address(dump_to='from', load_from='from')
    to = Address()


class UserTokenEventSchema(TokenEventSchema):
    direction = fields.Str()
    counterParty = Address(attribute='counter_party')
    user = Address()


class ExchangeEventSchema(BlockchainEventSchema):
    exchangeAddress = Address(attribute='exchange_address')
    makerTokenAddress = Address(attribute='maker_token')
    takerTokenAddress = Address(attribute='taker_token')
    from_ = Address(dump_to='from', load_from='from')
    orderHash = HexBytes(attribute='order_hash')
    filledMakerAmount = BigInteger(attribute='filled_maker_amount')
    filledTakerAmount = BigInteger(attribute='filled_taker_amount')
    cancelledMakerAmount = BigInteger(attribute='cancelled_maker_amount')
    cancelledTakerAmount = BigInteger(attribute='cancelled_taker_amount')
    to = Address()


class UserExchangeEventSchema(ExchangeEventSchema):
    direction = fields.Str()


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


class TxInfosSchema(Schema):
    class Meta:
        strict = True

    balance = BigInteger()
    nonce = fields.Integer()
    gasPrice = BigInteger(attribute='gas_price')
