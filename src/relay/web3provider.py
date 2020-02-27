import logging
from enum import Enum
from typing import MutableMapping

from web3 import HTTPProvider, IPCProvider, WebsocketProvider
from web3.providers.auto import load_provider_from_uri

logger = logging.getLogger("web3provider")


class ProviderType(Enum):
    HTTP = "http"
    WEBSOCKET = "websocket"
    IPC = "ipc"


def create_provider_from_config(rpc_config: MutableMapping):
    uri = rpc_config.get("uri", None)
    if uri is not None:
        logger.info(f"Autodetect provider from uri {uri}")
        provider = load_provider_from_uri(uri)
        logger.info(f"Autodetected {provider.__class__.__name__}")
        return provider

    provider_type = rpc_config["type"]
    if provider_type is ProviderType.HTTP:
        url = "{}://{}:{}".format(
            "https" if rpc_config["use_ssl"] else "http",
            rpc_config["host"],
            rpc_config["port"],
        )
        logger.info("Using HTTP provider with URL {}".format(url))
        return HTTPProvider(url)
    elif provider_type is ProviderType.WEBSOCKET:
        url = "{}://{}:{}".format(
            "wss" if rpc_config["use_ssl"] else "ws",
            rpc_config["host"],
            rpc_config["port"],
        )
        logger.info("Using websocket provider with URL {}".format(url))
        return WebsocketProvider(url)
    elif provider_type is ProviderType.IPC:
        file_path = rpc_config["file_path"]
        logger.info("Using IPC provider with file path {}".format(file_path))
        return IPCProvider(file_path)
    else:
        raise ValueError(f"Unknown web3 provider type: {provider_type}")
