from eth_utils import is_address, to_checksum_address
from marshmallow import Schema, ValidationError, fields, pre_load, validates_schema

from relay.blockchain.delegate import GasPriceMethod
from relay.web3provider import ProviderType


class LoggingField(fields.Mapping):
    pass


class AddressField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return to_checksum_address(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if not is_address(value):
            raise ValidationError(
                f"Could not parse attribute {attr}: Invalid address {value}"
            )

        return to_checksum_address(value)


class FeeSettingsSchema(Schema):
    base_fee = fields.Integer(missing=0)
    gas_price = fields.Integer(missing=0)
    fee_recipient = AddressField()
    currency_network = AddressField(required=True)


class GasPriceComputationSchema(Schema):
    method = fields.String(missing="rpc")
    gas_price = fields.Integer(missing=0)


class FaucetSchema(Schema):
    enable = fields.Boolean(missing=False)


class TrustlineIndexSchema(Schema):
    enable = fields.Boolean(missing=True)
    full_sync_interval = fields.Integer(missing=300)
    event_query_timeout = fields.Integer(missing=20)


class GasPriceMethodField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):

        if isinstance(value, GasPriceMethod):
            # serialises into the value of the enum
            return value.value
        else:
            raise ValidationError("Value must be of type GasPriceMethod")

    def _deserialize(self, value, attr, data, **kwargs):

        # deserialize into the enum instance corresponding to the value
        try:
            return GasPriceMethod(value)
        except ValueError:
            raise ValidationError(
                f"Could not parse attribute {attr}: {value} has to be one of "
                f"{[gas_price_method.value for gas_price_method in GasPriceMethod]}"
            )


class DelegateSchema(Schema):
    enable = fields.Boolean(missing=True)
    enable_deploy_identity = fields.Boolean(missing=True)
    fees = fields.List(fields.Nested(FeeSettingsSchema()), missing=list)
    gas_price_method = GasPriceMethodField(missing=GasPriceMethod.RPC)
    gas_price = fields.Integer()
    min_gas_price = fields.Integer()
    max_gas_price = fields.Integer()
    max_gas_limit = fields.Integer(missing=1_000_000)

    @validates_schema
    def validate_gas_price_method(self, in_data, **kwargs):
        gas_price_method = in_data["gas_price_method"]
        is_gas_price_given = "gas_price" in in_data
        is_min_gas_price_given = "min_gas_price" in in_data
        is_max_gas_price_given = "max_gas_price" in in_data

        if gas_price_method is GasPriceMethod.FIXED:
            if not is_gas_price_given:
                raise ValidationError(
                    "For gas price method: fixed, 'gas_price' must be set"
                )
        else:
            if is_gas_price_given:
                raise ValidationError(
                    "'gas_price' can only be set for gas price method: fixed"
                )

        if gas_price_method is GasPriceMethod.BOUND:
            if not is_min_gas_price_given or not is_max_gas_price_given:
                raise ValidationError(
                    "For gas price method: bound, 'min_gas_price' and 'max_gas_price' must be set"
                )
        else:
            if is_min_gas_price_given or is_max_gas_price_given:
                raise ValidationError(
                    "'min_gas_price' and 'max_gas_price' can only be set for gas price method: bound"
                )


class ExchangeSchema(Schema):
    enable = fields.Boolean(missing=True)


class TxRelaySchema(Schema):
    enable = fields.Boolean(missing=True)


class MessagingSchema(Schema):
    enable = fields.Boolean(missing=True)


class PushNotificationSchema(Schema):
    enable = fields.Boolean(missing=False)
    firebase_credentials_path = fields.String(missing="firebaseAccountKey.json")


class RESTSchema(Schema):
    host = fields.String(missing="")
    port = fields.Integer(missing=5000)


class ProviderTypeField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):

        if isinstance(value, ProviderType):
            # serialises into the value of the enum
            return value.value
        else:
            raise ValidationError("Value must be of type ProviderType")

    def _deserialize(self, value, attr, data, **kwargs):

        # deserialize into the enum instance corresponding to the value
        try:
            return ProviderType(value)
        except ValueError:
            raise ValidationError(
                f"Could not parse attribute {attr}: {value} has to be one of "
                f"{[possible_value.value for possible_value in ProviderType]}"
            )


class ChainNodeRPCSchema(Schema):
    type = ProviderTypeField(missing=ProviderType.HTTP)
    host = fields.String(missing="localhost")
    port = fields.Integer(missing=8545)
    use_ssl = fields.Boolean(missing=False)
    file_path = fields.String()
    uri = fields.String()

    @validates_schema(pass_original=True)
    def validate_only_one_provider(self, in_data, original_data, **kwargs):
        is_uri_set = "uri" in in_data
        is_provider_type_given = "type" in original_data

        provider_type = in_data["type"]

        if is_uri_set and is_provider_type_given:
            raise ValidationError("'uri' and 'type' can not be set at the same time")

        is_file_path_set = "file_path" in in_data
        if provider_type is ProviderType.IPC:
            if not is_file_path_set:
                raise ValidationError("ipc provider requires 'file_path' to be set")
        else:
            if is_file_path_set:
                raise ValidationError("'file_path' can only be set with type ipc")


class RelaySchema(Schema):
    update_indexed_networks_interval = fields.Integer(missing=120)
    gas_price_computation = fields.Nested(GasPriceComputationSchema())
    addresses_filepath = fields.String(missing="addresses.json")

    @pre_load
    def load_defaults(self, data, **kwargs):
        """Loads the missing Schemas that support all values missing"""
        for field_name in ["gas_price_computation"]:
            data[field_name] = {}
        return data


class AccountSchema(Schema):
    keystore_path = fields.String(required=True)
    keystore_password_path = fields.String(required=True)


class SentrySchema(Schema):
    dsn = fields.String(required=True)


class ConfigSchema(Schema):
    relay = fields.Nested(RelaySchema())
    faucet = fields.Nested(FaucetSchema())
    trustline_index = fields.Nested(TrustlineIndexSchema())
    delegate = fields.Nested(DelegateSchema())
    exchange = fields.Nested(ExchangeSchema())
    tx_relay = fields.Nested(TxRelaySchema())
    messaging = fields.Nested(MessagingSchema())
    push_notification = fields.Nested(PushNotificationSchema())
    rest = fields.Nested(RESTSchema())
    node_rpc = fields.Nested(ChainNodeRPCSchema())
    logging = LoggingField()
    sentry = fields.Nested(SentrySchema())
    account = fields.Nested(AccountSchema())

    @pre_load
    def load_defaults(self, data, **kwargs):
        """Loads the missing Schemas that support all values missing"""
        # Put exceptions here
        needs_values = {"account", "sentry"}
        for field_name in self.fields.keys():
            if field_name not in needs_values and field_name not in data:
                data[field_name] = {}
        return data
