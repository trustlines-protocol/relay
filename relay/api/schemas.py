from marshmallow import Schema, fields
from marshmallow_oneofschema import OneOfSchema

from .fields import Address, BigInteger, HexBytes

from relay.blockchain.unw_eth_events import UnwEthEvent
from relay.blockchain.exchange_events import ExchangeEvent
from relay.blockchain.currency_network_events import CurrencyNetworkEvent


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
    given = BigInteger(attribute='creditline_given')
    received = BigInteger(attribute='creditline_received')
    balance = BigInteger()
    interestRateGiven = BigInteger(attribute='interest_rate_given')
    interestRateReceived = BigInteger(attribute='interest_rate_received')
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


class AnyEventSchema(OneOfSchema):
    type_schemas = {
        'CurrencyNetworkEvent': UserCurrencyNetworkEventSchema,
        'UnwEthEvent': UserTokenEventSchema,
        'ExchangeEvent': ExchangeEventSchema,
    }

    type_field = '__class__'

    def get_obj_type(self, obj):
        if isinstance(obj, CurrencyNetworkEvent):
            return "CurrencyNetworkEvent"
        elif isinstance(obj, UnwEthEvent):
            return "UnwEthEvent"
        elif isinstance(obj, ExchangeEvent):
            return "ExchangeEvent"

        raise RuntimeError(f'Unknown object type: {obj.__class__.__name__}')


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
    interestRateGiven = BigInteger(attribute='interest_rate_given')
    interestRateReceived = BigInteger(attribute='interest_rate_received')
    given = BigInteger(attribute='creditline_given')
    received = BigInteger(attribute='creditline_received')
    balance = BigInteger()
    user = Address()
    counterParty = Address()
    address = Address()
    id = Address()


class TxInfosSchema(Schema):
    class Meta:
        strict = True

    balance = BigInteger()
    nonce = fields.Integer()
    gasPrice = BigInteger(attribute='gas_price')


class CurrencyNetworkSchema(Schema):
    class Meta:
        strict = True

    abbreviation = fields.Str(attribute='symbol')
    name = fields.Str()
    address = Address()
    decimals = fields.Int()
    numUsers = fields.Int(attribute='num_users')
    defaultInterestRate = BigInteger(attribute='default_interest_rate')
    interestRateDecimals = fields.Int(attribute='interest_rate_decimals')
    customInterests = fields.Bool(attribute='custom_interests')
    preventMediatorInterests = fields.Bool(attribute='prevent_mediator_interests')


class PaymentPathSchema(Schema):
    class Meta:
        strict = True
    fees = BigInteger(required=True, attribute="fee")
    path = fields.List(Address(), required=True)
    estimatedGas = BigInteger(attribute="estimated_gas")
    value = BigInteger()
