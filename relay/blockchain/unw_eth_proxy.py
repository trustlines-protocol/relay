import logging

from .proxy import Proxy
from relay.exchange.order import Order
from relay.logger import get_logger

logger = get_logger('token', logging.DEBUG)

FillEvent = 'LogFill'
CancelEvent = 'LogCancel'


class UnwEthProxy(Proxy):
    def __init__(
            self,
            web3,
            unw_eth_abi,
            address: str
    ) -> None:
        super().__init__(web3, unw_eth_abi, address)

