from eth_utils import is_address, to_checksum_address
from marshmallow import (
    Schema,
    ValidationError as MarshmallowValidationError,
    fields,
    pre_load,
)


class LoggingField(fields.Mapping):
    pass


class AddressField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        return to_checksum_address(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if not is_address(value):
            raise MarshmallowValidationError(
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


class DelegateSchema(Schema):
    enable = fields.Boolean(missing=True)
    enable_deploy_identity = fields.Boolean(missing=True)
    fees = fields.List(fields.Nested(FeeSettingsSchema()), missing=list)


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


class ChainNodeRPCSchema(Schema):
    host = fields.String(missing="localhost")
    port = fields.Integer(missing=8545)
    use_ssl = fields.Boolean(missing=False)


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
