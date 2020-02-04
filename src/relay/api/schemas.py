import hexbytes
from marshmallow import Schema, ValidationError, fields, post_load
from marshmallow_oneofschema import OneOfSchema
from tldeploy import identity
from tldeploy.identity import MetaTransaction

from relay.blockchain.currency_network_events import CurrencyNetworkEvent
from relay.blockchain.exchange_events import ExchangeEvent
from relay.blockchain.unw_eth_events import UnwEthEvent
from relay.network_graph.payment_path import PaymentPath

from .fields import (
    Address,
    BigInteger,
    FeePayerField,
    HexBytes,
    HexEncodedBytes,
    OperationTypeField,
)

ZERO_ADDRESS = "0x" + "0" * 40


class MetaTransactionSchema(Schema):
    class Meta:
        strict = True

    def _validate(self, data):
        value = data["value"]
        nonce = data["nonce"]
        base_fee = data["base_fee"]
        gas_price = data["gas_price"]
        gas_limit = data["gas_limit"]
        signature = data["signature"]
        if not 0 <= value < 2 ** 256:
            raise ValidationError(f"value={value} is out of bounds")
        if not 0 <= nonce < 2 ** 256:
            raise ValidationError(f"nonce={nonce} is out of bounds")
        if not 0 <= base_fee < 2 ** 256:
            raise ValidationError(f"baseFee={base_fee} is out of bounds")
        if not 0 <= gas_price < 2 ** 256:
            raise ValidationError(f"gas_price={gas_price} is out of bounds")
        if not 0 <= gas_limit < 2 ** 256:
            raise ValidationError(f"gas_limit={gas_limit} is out of bounds")
        if len(signature) != 65 and signature != hexbytes.HexBytes(""):
            raise ValidationError("signature must be 65 bytes")

    @post_load
    def make_meta_transaction(self, data, partial, many):
        self._validate(data)
        return identity.MetaTransaction(**data)

    chainId = fields.Integer(missing=0, attribute="chain_id")
    version = fields.Integer(missing=0, attribute="version")
    from_ = Address(required=True, data_key="from")
    to = Address(required=True)
    value = BigInteger(required=True)
    data = HexEncodedBytes(required=True)
    baseFee = BigInteger(missing=0, attribute="base_fee")
    gasPrice = BigInteger(missing=0, attribute="gas_price")
    gasLimit = BigInteger(missing=0, attribute="gas_limit")
    feeRecipient = Address(missing=ZERO_ADDRESS, attribute="fee_recipient")
    currencyNetworkOfFees = Address(missing=to, attribute="currency_network_of_fees")
    nonce = BigInteger(required=True)
    timeLimit = fields.Integer(missing=0, attribute="time_limit")
    operationType = OperationTypeField(
        missing=MetaTransaction.OperationType.CALL, attribute="operation_type"
    )
    signature = HexEncodedBytes(missing=hexbytes.HexBytes(""))


class MetaTransactionFeeSchema(Schema):
    class Meta:
        strict = True

    baseFee = BigInteger(required=True, attribute="base_fee")
    gasPrice = BigInteger(required=True, attribute="gas_price")
    feeRecipient = Address(required=True, attribute="fee_recipient")
    currencyNetworkOfFees = Address(required=True, attribute="currency_network_of_fees")


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
    currencyNetwork = Address()


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
    isFrozen = fields.Bool(attribute="is_frozen")


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


class AccruedInterestSchema(Schema):
    class Meta:
        strict = True

    value = BigInteger()
    interestRate = fields.Int(attribute="interest_rate")
    timestamp = fields.Integer()


class AccruedInterestListSchema(Schema):
    class Meta:
        strict = True

    accruedInterests = fields.Nested(AccruedInterestSchema, many=True)
    user = Address()
    counterparty = Address()
