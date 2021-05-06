import hexbytes
from marshmallow import (
    Schema,
    ValidationError,
    fields,
    post_dump,
    post_load,
    validates_schema,
)
from marshmallow.validate import Range
from marshmallow_oneofschema import OneOfSchema
from tldeploy import identity
from tldeploy.identity import MetaTransaction

from relay.blockchain.currency_network_events import CurrencyNetworkEvent
from relay.blockchain.exchange_events import ExchangeEvent
from relay.blockchain.token_events import TokenEvent
from relay.blockchain.unw_eth_events import UnwEthEvent
from relay.network_graph.payment_path import PaymentPath

from .fields import (
    Address,
    BigInteger,
    FeePayerField,
    Hash,
    HexBytes,
    HexEncodedBytes,
    MetaTransactionStatusField,
    OperationTypeField,
    TransactionStatusField,
)

ZERO_ADDRESS = "0x" + "0" * 40


class MetaTransactionSchema(Schema):
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

    baseFee = BigInteger(required=True, attribute="base_fee")
    gasPrice = BigInteger(required=True, attribute="gas_price")
    feeRecipient = Address(required=True, attribute="fee_recipient")
    currencyNetworkOfFees = Address(required=True, attribute="currency_network_of_fees")

    @post_dump()
    def set_default_currency_network(self, data, **kwargs):
        data = {**data}
        # TODO Remove in future version
        # Only here for backwards compatibility with clientlib v0.12.1 and lower
        if data["currencyNetworkOfFees"] is None:
            data["currencyNetworkOfFees"] = ZERO_ADDRESS
        return data


class AppliedDelegationFeeSchema(Schema):

    feeSender = Address(required=True, attribute="from_")
    feeRecipient = Address(required=True, attribute="to")
    totalFee = BigInteger(required=True, attribute="value")
    currencyNetworkOfFees = Address(required=True, attribute="currency_network")


class MetaTransactionStatusSchema(Schema):

    status = MetaTransactionStatusField(required=True)


class TransactionStatusSchema(Schema):

    status = TransactionStatusField(required=True)


class EventSchema(Schema):

    timestamp = fields.Integer()


class MessageEventSchema(EventSchema):
    message = fields.Str()


class BlockchainEventSchema(EventSchema):
    blockNumber = fields.Integer(attribute="blocknumber")
    type = fields.Str(default="event")
    transactionId = HexBytes(
        attribute="transaction_hash", dump_only=True
    )  # TODO: Deprecated, remove in future release
    transactionHash = HexBytes(attribute="transaction_hash")
    status = fields.Str()
    blockHash = HexBytes(attribute="block_hash")
    logIndex = fields.Int(attribute="log_index")


class CurrencyNetworkEventSchema(BlockchainEventSchema):
    networkAddress = Address(attribute="network_address")
    amount = BigInteger(attribute="value")
    given = BigInteger(attribute="creditline_given")
    received = BigInteger(attribute="creditline_received")
    balance = BigInteger()
    interestRateGiven = BigInteger(attribute="interest_rate_given")
    interestRateReceived = BigInteger(attribute="interest_rate_received")
    isFrozen = fields.Bool(attribute="is_frozen")
    transfer = BigInteger(attribute="transfer")
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
        "TokenEventSchema": UserTokenEventSchema,
    }

    # To not override the 'type' field
    type_field = "__class__"

    def get_obj_type(self, obj):
        if isinstance(obj, CurrencyNetworkEvent):
            return "CurrencyNetworkEvent"
        elif isinstance(obj, UnwEthEvent):
            return "UnwEthEvent"
        elif isinstance(obj, ExchangeEvent):
            return "ExchangeEvent"
        elif isinstance(obj, TokenEvent):
            return "TokenEventSchema"

        raise RuntimeError(f"Unknown object type: {obj.__class__.__name__}")

    def _dump(self, obj, *, update_fields=True, **kwargs):
        # Remove the type_field again. Sadly post hooks and exclude of marshmallow do not work
        result = super()._dump(obj, update_fields=update_fields, **kwargs)
        del result[self.type_field]
        return result


class AggregatedAccountSummarySchema(Schema):

    leftGiven = BigInteger(attribute="creditline_left_given")
    leftReceived = BigInteger(attribute="creditline_left_received")
    given = BigInteger(attribute="creditline_given")
    received = BigInteger(attribute="creditline_received")
    balance = BigInteger()
    frozenBalance = BigInteger(attribute="frozen_balance")


class TrustlineSchema(Schema):

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

    balance = BigInteger()
    nonce = fields.Integer()
    gasPrice = BigInteger(attribute="gas_price")


class IdentityInfosSchema(Schema):

    balance = BigInteger()
    nextNonce = fields.Integer()
    identity = Address()
    implementationAddress = Address()


class CurrencyNetworkSchema(Schema):

    abbreviation = fields.Str(attribute="symbol")
    name = fields.Str()
    address = Address()
    decimals = fields.Int()
    numUsers = fields.Int(attribute="num_users")
    capacityImbalanceFeeDivisor = fields.Int(attribute="capacity_imbalance_fee_divisor")
    defaultInterestRate = BigInteger(attribute="default_interest_rate")
    interestRateDecimals = fields.Int(attribute="interest_rate_decimals")
    customInterests = fields.Bool(attribute="custom_interests")
    preventMediatorInterests = fields.Bool(attribute="prevent_mediator_interests")
    isFrozen = fields.Bool(attribute="is_frozen")


class PaymentPathSchema(Schema):
    @post_load
    def make_payment_path(self, data, partial, many):
        return PaymentPath(**data)

    fees = BigInteger(required=True, attribute="fee")
    path = fields.List(Address(), required=True)
    value = BigInteger()
    feePayer = FeePayerField(required=True, attribute="fee_payer")


class AccruedInterestSchema(Schema):

    value = BigInteger()
    interestRate = fields.Int(attribute="interest_rate")
    timestamp = fields.Integer()


class AccruedInterestListSchema(Schema):

    accruedInterests = fields.Nested(AccruedInterestSchema, many=True)
    user = Address()
    counterparty = Address()


class MediationFeeSchema(Schema):

    value = BigInteger()
    from_ = Address(data_key="from")
    to = Address()
    transactionHash = HexEncodedBytes(attribute="transaction_hash")
    timestamp = fields.Integer()


class MediationFeesListSchema(Schema):

    mediationFees = fields.Nested(MediationFeeSchema, many=True)
    user = Address()
    network = Address()


class DebtsSchema(Schema):

    debtor = Address(required=True)
    value = BigInteger(required=True)
    maximumClaimableValue = BigInteger(required=True, attribute="claimable_value")
    claimPath = fields.List(Address(), required=False, attribute="claim_path")


class DebtsListInCurrencyNetworkSchema(Schema):

    currencyNetwork = Address(required=True, attribute="currency_network")
    debts = fields.Nested(DebtsSchema, many=True, attribute="debts_list")


class TransferInformationSchema(Schema):

    currencyNetwork = Address(required=True, attribute="currency_network")
    path = fields.List(Address(), required=True)
    value = BigInteger(required=True)
    feePayer = FeePayerField(required=True, attribute="fee_payer")
    totalFees = BigInteger(required=True, attribute="total_fees")
    feesPaid = fields.List(BigInteger(), required=True, attribute="fees_paid")
    extraData = HexEncodedBytes(required=True, attribute="extra_data")


class TransferIdentifierSchema(Schema):
    @validates_schema
    def validate(self, data, partial, many):
        transaction_hash = data["transactionHash"]
        block_hash = data["blockHash"]
        log_index = data["logIndex"]
        if transaction_hash is not None and (
            block_hash is not None or log_index is not None
        ):
            raise ValidationError(
                "Cannot get transfer information using transaction hash and log index or block hash."
            )
        elif block_hash is not None and log_index is None:
            raise ValidationError(
                "Cannot get transfer information using block hash if log index not provided."
            )
        elif log_index is not None and block_hash is None:
            raise ValidationError(
                "Cannot get transfer information using log index if block hash not provided."
            )
        elif log_index is None and block_hash is None and transaction_hash is None:
            raise ValidationError(
                "Either transaction hash or block hash and log index need to be provided."
            )

    transactionHash = Hash(required=False, missing=None)
    blockHash = Hash(required=False, missing=None)
    logIndex = fields.Int(required=False, missing=None, validate=Range(min=0))


class TransactionIdentifierSchema(Schema):

    transactionHash = Hash(required=True)


class TransferredSumSchema(Schema):

    sender = Address(required=True)
    receiver = Address(required=True)
    startTime = fields.Integer(required=True)
    endTime = fields.Integer(required=True)
    value = BigInteger(required=True)
