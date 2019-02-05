import hexbytes
from webargs import ValidationError
from marshmallow import fields
from eth_utils import is_address, to_checksum_address


class Address(fields.String):

    def _serialize(self, value, attr, obj):
        return super()._serialize(value, attr, obj)

    def _deserialize(self, value, attr, data):
        value = super()._deserialize(value, attr, data)

        if not is_address(value):
            raise ValidationError('Invalid Address')

        return to_checksum_address(value)


class BigInteger(fields.String):

    def _serialize(self, value, attr, obj):
        value = str(value)
        return super()._serialize(value, attr, obj)

    def _deserialize(self, value, attr, data):
        value = super()._deserialize(value, attr, data)

        try:
            int_value = int(value)
        except ValueError:
            raise ValidationError('Could not parse Integer')

        return int_value


class HexBytes(fields.String):

    def _serialize(self, value, attr, obj):
        return '0x{:064X}'.format(int.from_bytes(value, 'big')).lower()

    def _deserialize(self, value, attr, data):
        value = super()._deserialize(value, attr, data)
        try:
            hex_bytes = hexbytes.HexBytes(value)
        except ValueError:
            raise ValidationError('Could not parse Hex number')

        return hex_bytes


class HexEncodedBytes(fields.Field):
    """hex encoded bytes field, correctly round-trips. was needed because
    HexBytes doesn't round trip correctly """

    def _serialize(self, value, attr, obj):
        assert isinstance(value, bytes)
        return "0x" + value.hex()

    def _deserialize(self, value, attr, data):
        if not value.startswith("0x"):
            raise ValidationError(
                f"Could not parse hex-encoded bytes objects of attribute {attr}: {value}"
            )
        try:
            return bytes.fromhex(value[2:])
        except ValueError:
            raise ValidationError(
                f"Could not parse hex-encoded bytes objects of attribute {attr}: {value}"
            )
