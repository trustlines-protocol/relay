import logging
from typing import Dict, Iterable, List, MutableMapping, Union

import toml
from marshmallow import ValidationError
from toolz import get_in, update_in

from .schema import ConfigSchema

logger = logging.getLogger("config")


def load_config(path: str) -> MutableMapping:
    raw_data = toml.load(path)
    raw_data = convert_legacy_format(raw_data)
    return ConfigSchema().load(raw_data)


def dump_config(config: MutableMapping, path: str) -> None:
    with open(path, "w") as file:
        toml.dump(ConfigSchema().dump(config), file)


def dump_default_config(path: str) -> None:
    dump_config(generate_default_config(), path)


def generate_default_config() -> MutableMapping:
    return ConfigSchema().load({})


def validation_error_string(validation_error: ValidationError) -> str:
    """Creates a readable error message string from a validation error"""
    messages = validation_error.messages

    def _validation_error_string(
        whole_key: str, messages: Dict[str, Union[str, List[str], Dict]]
    ):
        error_list: List[str] = []
        for key, value in messages.items():
            if key != "_schema":
                key = f"{whole_key}.{key}"
            else:
                # Ignore _schema in key
                key = whole_key
            if isinstance(value, str):
                error_list.append(f"{key}: {value}")
            elif isinstance(value, list):
                for v in value:
                    error_list.append(f"{key}: {v}")
            else:
                error_list.extend(_validation_error_string(key, value))
        return error_list

    if isinstance(messages, list):
        error_list = messages
    else:
        error_list = _validation_error_string("", messages)
    return ", ".join(error_list)


def convert_legacy_format(raw_data: MutableMapping) -> MutableMapping:
    """Convert old legacy config settings to new ones"""

    def convert_delegation_fees(old_fees):
        new_fees = []
        for old_fee in old_fees:
            new_fee = {}
            mapping = {
                "baseFee": "base_fee",
                "gasPrice": "gas_price",
                "feeRecipient": "fee_recipient",
                "currencyNetworkOfFees": "currency_network",
            }
            for old_key, new_key in mapping.items():
                value = old_fee.get(old_key, None)
                if value is not None:
                    new_fee[new_key] = value

            new_fees.append(new_fee)
        return new_fees

    old_delegation_key = "relay.delegationFees"
    if _get_nested_dict(raw_data, old_delegation_key) is not None:
        raw_data = _update_nested_dict(
            raw_data,
            old_delegation_key,
            convert_delegation_fees(_get_nested_dict(raw_data, old_delegation_key)),
        )

    mapping_old_config_format: Dict[str, str] = {
        "relay.enableEtherFaucet": "faucet.enable",
        "relay.enableRelayMetaTransaction": "delegate.enable",
        "relay.enableDeployIdentity": "delegate.enable_deploy_identity",
        "relay.rpc": "node_rpc",
        "node_rpc.ssl": "node_rpc.use_ssl",
        "relay.gasPriceComputation.method": "relay.gas_price_computation.method",
        "relay.gasPriceComputation.gasPrice": "relay.gas_price_computation.gas_price",
        "relay.delegationFees": "delegate.fees",
        "relay.sentry": "sentry",
        "relay.firebase.credentialsPath": "push_notification.firebase_credentials_path",
    }
    not_supported_anymore_config = [
        "trustline_index.event_query_timeout",
        "relay.eventQueryTimeout",
        "relay.updateNetworksInterval",
        "relay.update_indexed_networks_interval",
    ]
    deprecated_config: Iterable[str] = [
        "trustline_index.full_sync_interval",
        "relay.syncInterval",
    ]
    for old_path, new_path in mapping_old_config_format.items():
        raw_data = _remap_config_entry(raw_data, old_path, new_path)
    raw_data = _handle_deprecated_config(raw_data, deprecated_config)
    _handle_not_supported_config(raw_data, not_supported_anymore_config)
    return _remove_empty_dicts(raw_data)


def _update_nested_dict(d, path: str, value):
    return update_in(d, path.split("."), lambda x: value)


def _get_nested_dict(d, path: str, default=None):
    return get_in(path.split("."), d, default=default)


def _remap_config_entry(d, old_path: str, new_path: str):
    value = _get_nested_dict(d, old_path)
    if value is not None:
        if _get_nested_dict(d, new_path) is not None:
            raise ValidationError(
                {
                    old_path: f"Old entry can not be set if new entry {new_path} is also set"
                }
            )
        logger.warning(f"{old_path} is deprecated, please use {new_path}")
        # mark as can be deleted with None
        d = _update_nested_dict(d, old_path, None)
        d = _update_nested_dict(d, new_path, value)
    return d


def _handle_deprecated_config(config, deprecated_keys: Iterable[str]):
    for deprecated_key in deprecated_keys:
        value = _get_nested_dict(config, deprecated_key)
        if value is not None:
            logger.warning(
                f"{deprecated_key} is deprecated, please remove it from the relay config"
            )
            config = _update_nested_dict(config, deprecated_key, None)
    return config


def _handle_not_supported_config(config, not_supported_keys: Iterable[str]):
    for key in not_supported_keys:
        value = _get_nested_dict(config, key)
        if value is not None:
            raise ValidationError({not_supported_keys: "Not supported anymore"})


def _remove_empty_dicts(data: MutableMapping, factory=dict) -> MutableMapping:
    """Recursively removes None entries and empty dicts from a nested dict"""
    d = factory()

    for key, value in data.items():
        if value is None:
            # Remove
            pass
        elif isinstance(value, Dict):
            sub_dict = _remove_empty_dicts(value, factory=factory)
            if sub_dict:
                d[key] = sub_dict
        else:
            d[key] = value

    return d
