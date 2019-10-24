from marshmallow import Schema, ValidationError, fields, post_load
from marshmallow_oneofschema import OneOfSchema
from tldeploy import identity

from relay.blockchain.currency_network_events import CurrencyNetworkEvent
from relay.blockchain.exchange_events import ExchangeEvent
from relay.blockchain.unw_eth_events import UnwEthEvent
from relay.network_graph.payment_path import PaymentPath

from .fields import Address, BigInteger, FeePayerField, HexBytes, HexEncodedBytes


class MetaTransactionSchema(Schema):
    class Meta:
        strict = True

    def _validate(self, data):
        nonce = data["nonce"]
        fees = data["fees"]
        if not 0 <= nonce < 2 ** 256:
            raise ValidationError(f"nonce={nonce} is out of bounds")
        if not 0 <= fees < 2 ** 64:
            raise ValidationError(f"delegationFees={fees} is out of bounds")
        if len(data["signature"]) != 65:
            raise ValidationError("signature must be 65 bytes")

        value = data["value"]
        if not 0 <= value < 2 ** 256:
            raise ValidationError(f"value={value} is out of bounds")

    @post_load
    def make_meta_transaction(self, data, partial, many):
        self._validate(data)
        return identity.MetaTransaction(**data)

    from_ = Address(required=True, data_key="from")
    to = Address(required=True)
    value = BigInteger(required=True)
    data = HexEncodedBytes(required=True)
    delegationFees = BigInteger(missing=0, attribute="fees")
    currencyNetworkOfFees = Address(missing=to, attribute="currency_network_of_fees")
    nonce = BigInteger(required=True)
    extraData = HexEncodedBytes(required=True, attribute="extra_data")
    signature = HexEncodedBytes(required=True)


class EventSchema(Schema):
    class Meta:
        strict = True

    timestamp = fields.Integer()


class MessageEventSchema(EventSchema):
    message = fields.Str()


class BlockchainEventSchema(EventSchema):
    blockNumber = fields.Integer(attribute="blocknumber")
    type = fields.Str(default="event")
    transactionId = HexBytes(attribute="transaction_id")
    status = fields.Str()


class CurrencyNetworkEventSchema(BlockchainEventSchema):
    networkAddress = Address(attribute="network_address")
    amount = BigInteger(attribute="value")
    given = BigInteger(attribute="creditline_given")
    received = BigInteger(attribute="creditline_received")
    balance = BigInteger()
    interestRateGiven = BigInteger(attribute="interest_rate_given")
    interestRateReceived = BigInteger(attribute="interest_rate_received")
    isFrozen = fields.Bool(attribute="is_frozen")
    leftGiven = BigInteger(attribute="left_given")
    leftReceived = BigInteger(attribute="left_received")
    from_ = Address(data_key="from")
    to = Address()
    extraData = HexEncodedBytes(attribute="extra_data")


class UserCurrencyNetworkEventSchema(CurrencyNetworkEventSchema):
    direction = fields.Str()
    counterParty = Address(attribute="counter_party")
    user = Address()


class TokenEventSchema(BlockchainEventSchema):
    tokenAddress = Address(attribute="token_address")
    amount = BigInteger(attribute="value")
    from_ = Address(data_key="from")
    to = Address()


class UserTokenEventSchema(TokenEventSchema):
    direction = fields.Str()
    counterParty = Address(attribute="counter_party")
    user = Address()


class ExchangeEventSchema(BlockchainEventSchema):
    exchangeAddress = Address(attribute="exchange_address")
    makerTokenAddress = Address(attribute="maker_token")
    takerTokenAddress = Address(attribute="taker_token")
    from_ = Address(data_key="from")
    orderHash = HexBytes(attribute="order_hash")
    filledMakerAmount = BigInteger(attribute="filled_maker_amount")
    filledTakerAmount = BigInteger(attribute="filled_taker_amount")
    cancelledMakerAmount = BigInteger(attribute="cancelled_maker_amount")
    cancelledTakerAmount = BigInteger(attribute="cancelled_taker_amount")
    to = Address()


class UserExchangeEventSchema(ExchangeEventSchema):
    direction = fields.Str()


class AnyEventSchema(OneOfSchema):
    type_schemas = {
        "CurrencyNetworkEvent": UserCurrencyNetworkEventSchema,
        "UnwEthEvent": UserTokenEventSchema,
        "ExchangeEvent": ExchangeEventSchema,
    }

    type_field = "__class__"

    def get_obj_type(self, obj):
        if isinstance(obj, CurrencyNetworkEvent):
            return "CurrencyNetworkEvent"
        elif isinstance(obj, UnwEthEvent):
            return "UnwEthEvent"
        elif isinstance(obj, ExchangeEvent):
            return "ExchangeEvent"

        raise RuntimeError(f"Unknown object type: {obj.__class__.__name__}")


class AggregatedAccountSummarySchema(Schema):
    class Meta:
        strict = True

    leftGiven = BigInteger(attribute="creditline_left_given")
    leftReceived = BigInteger(attribute="creditline_left_received")
    given = BigInteger(attribute="creditline_given")
    received = BigInteger(attribute="creditline_received")
    balance = BigInteger()
    frozenBalance = BigInteger(attribute="frozen_balance")


class TrustlineSchema(Schema):
    class Meta:
        strict = True

    leftGiven = BigInteger(attribute="creditline_left_given")
    leftReceived = BigInteger(attribute="creditline_left_received")
    interestRateGiven = BigInteger(attribute="interest_rate_given")
    interestRateReceived = BigInteger(attribute="interest_rate_received")
    isFrozen = fields.Bool(attribute="is_frozen")
    given = BigInteger(attribute="creditline_given")
    received = BigInteger(attribute="creditline_received")
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
    gasPrice = BigInteger(attribute="gas_price")


class IdentityInfosSchema(Schema):
    class Meta:
        strict = True

    balance = BigInteger()
    nextNonce = fields.Integer()
    identity = Address()


class CurrencyNetworkSchema(Schema):
    class Meta:
        strict = True

    abbreviation = fields.Str(attribute="symbol")
    name = fields.Str()
    address = Address()
    decimals = fields.Int()
    numUsers = fields.Int(attribute="num_users")
    defaultInterestRate = BigInteger(attribute="default_interest_rate")
    interestRateDecimals = fields.Int(attribute="interest_rate_decimals")
    customInterests = fields.Bool(attribute="custom_interests")
    preventMediatorInterests = fields.Bool(attribute="prevent_mediator_interests")


class PaymentPathSchema(Schema):
    class Meta:
        strict = True

    @post_load
    def make_payment_path(self, data, partial, many):
        return PaymentPath(**data)

    fees = BigInteger(required=True, attribute="fee")
    path = fields.List(Address(), required=True)
    value = BigInteger()
    feePayer = FeePayerField(required=True, attribute="fee_payer")
