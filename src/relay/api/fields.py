import hexbytes
from eth_utils import is_address, to_checksum_address
from marshmallow import fields
from tldeploy.identity import MetaTransaction
from webargs import ValidationError

from relay.network_graph.payment_path import FeePayer


class Address(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return super()._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if not is_address(value):
            raise ValidationError(
                f"Could not parse attribute {attr}: Invalid address {value}"
            )

        return to_checksum_address(value)


class BigInteger(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        assert isinstance(value, int)
        value = str(value)
        return super()._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, str):
            raise ValidationError(f"{attr} has to be a string")
        try:
            int_value = int(value)
        except ValueError:
            raise ValidationError("Could not parse integer")

        return int_value


class HexBytes(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return "0x{:064X}".format(int.from_bytes(value, "big")).lower()

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            hex_bytes = hexbytes.HexBytes(value)
        except ValueError:
            raise ValidationError("Could not parse Hex number")

        return hex_bytes


class HexEncodedBytes(fields.Field):
    """hex encoded bytes field, correctly round-trips. was needed because
    HexBytes doesn't round trip correctly """

    def _serialize(self, value, attr, obj, **kwargs):
        if isinstance(value, hexbytes.HexBytes):
            return value.hex()
        elif isinstance(value, bytes):
            return "0x" + value.hex()
        else:
            raise ValueError("Value must be of type bytes or HexBytes")

    def _deserialize(self, value, attr, data, **kwargs):
        if not (isinstance(value, str) and value.startswith("0x")):
            raise ValidationError(
                f"Could not parse hex-encoded bytes objects of attribute {attr}: {value}"
            )
        try:
            # Create bytes first, to not use weird conversion done by hexbytes constructor
            return hexbytes.HexBytes(bytes.fromhex(value[2:]))
        except ValueError:
            raise ValidationError(
                f"Could not parse hex-encoded bytes objects of attribute {attr}: {value}"
            )


class FeePayerField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):

        if isinstance(value, FeePayer):
            # serialises into the value of the FeePayer enum
            return value.value
        else:
            raise ValidationError("Value must be of type FeePayer")

    def _deserialize(self, value, attr, data, **kwargs):

        # deserialize into the FeePayer enum instance corresponding to the value
        try:
            return FeePayer(value)
        except ValueError:
            raise ValidationError(
                f"Could not parse attribute {attr}: {value} has to be one of "
                f"{[fee_payer.value for fee_payer in FeePayer]}"
            )


class OperationTypeField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):

        if isinstance(value, MetaTransaction.OperationType):
            # serialises into the value of the OperationType enum
            return value.value
        else:
            raise ValidationError("Value must be of type OperationType")

    def _deserialize(self, value, attr, data, **kwargs):

        # deserialize into the OperationType enum instance corresponding to the value
        try:
            return MetaTransaction.OperationType(value)
        except ValueError:
            raise ValidationError(
                f"Could not parse attribute {attr}: {value} has to be one of "
                f"{[operation_type.value for operation_type in MetaTransaction.OperationType]}"
            )
