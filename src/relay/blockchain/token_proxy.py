import logging

from .proxy import Proxy

logger = logging.getLogger("token")


class TokenProxy(Proxy):
    def __init__(self, web3, token_abi, address: str) -> None:
        super().__init__(web3, token_abi, address)

    def balance_of(self, user_address: str):
        return self._proxy.functions.balanceOf(user_address).call()
