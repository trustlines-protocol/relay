from marshmallow import Schema, fields
from ..fields import Address, BigInteger, HexBytes


class SignatureSchema(Schema):
    class Meta:
        strict = True

    v = fields.Integer()
    r = HexBytes()
    s = HexBytes()


class OrderSchema(Schema):
    class Meta:
        strict = True

    exchangeContractAddress = Address(attribute='exchange_address')
    maker = Address(attribute='maker_address')
    taker = Address(attribute='taker_address')
    makerTokenAddress = Address(attribute='maker_token')
    takerTokenAddress = Address(attribute='taker_token')
    feeRecipient = Address(attribute='fee_recipient')
    makerTokenAmount = BigInteger(attribute='maker_token_amount')
    takerTokenAmount = BigInteger(attribute='taker_token_amount')
    filledMakerTokenAmount = BigInteger(attribute='filled_maker_token_amount')
    filledTakerTokenAmount = BigInteger(attribute='filled_taker_token_amount')
    cancelledMakerTokenAmount = BigInteger(attribute='cancelled_maker_token_amount')
    cancelledTakerTokenAmount = BigInteger(attribute='cancelled_taker_token_amount')
    availableMakerTokenAmount = BigInteger(attribute='available_maker_token_amount')
    availableTakerTokenAmount = BigInteger(attribute='available_taker_token_amount')
    makerFee = BigInteger(attribute='maker_fee')
    takerFee = BigInteger(attribute='taker_fee')
    expirationUnixTimestampSec = BigInteger(attribute='expiration_timestamp_in_sec')
    salt = BigInteger(attribute='salt')
    ecSignature = fields.Nested(SignatureSchema, attribute='ec_signature')
