import logging

from .proxy import Proxy
from relay.exchange.order import Order
from relay.logger import get_logger

logger = get_logger('token', logging.DEBUG)

FillEvent = 'LogFill'
CancelEvent = 'LogCancel'


class TokenProxy(Proxy):

    def __init__(self, web3, token_abi, address: str) -> None:
        super().__init__(web3, token_abi, address)

    def balance_of(self, user_address: str):
        return self._proxy.call().balanceOf(user_address)
