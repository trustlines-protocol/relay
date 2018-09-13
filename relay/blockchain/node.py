import logging
from collections import namedtuple

from relay.logger import get_logger


TxInfos = namedtuple('TxInfos', 'balance, nonce, gas_price')


logger = get_logger('node', logging.DEBUG)


class Node:

    def __init__(self, web3, is_parity=True):
        self._web3 = web3
        self.is_parity = is_parity
        if is_parity:
            logger.info('Assuming connected to parity node: Enabling parity-only rpc methods.')

    def relay_tx(self, rawtxn):
        return self._web3.eth.sendRawTransaction(rawtxn)

    def transaction_receipt(self, txn_hash):
        return self._web3.eth.getTransactionReceipt(txn_hash)

    def get_tx_infos(self, user_address, block_identifier='pending'):
        if self.is_parity and block_identifier == 'pending':
            nonce = int(self._web3.manager.request_blocking('parity_nextNonce', [user_address]), 16)
        else:
            nonce = self._web3.eth.getTransactionCount(user_address, block_identifier=block_identifier)
        return TxInfos(balance=self._web3.eth.getBalance(user_address, block_identifier=block_identifier),
                       nonce=nonce,
                       gas_price=self._web3.eth.gasPrice)

    @property
    def blocknumber(self):
        return self._web3.eth.blockNumber

    def balance(self, address):
        wei = self._web3.eth.getBalance(address)
        return str(self._web3.fromWei(wei, 'ether'))

    def send_ether(self, address):
        if self._web3.eth.getBalance(address) <= 5:
            return self._web3.eth.sendTransaction({
                'from': self._web3.eth.coinbase,
                'to': address,
                'value': 1000000000000000000
            })
        else:
            return None

    def get_block_timestamp(self, block_number):
        return self._web3.eth.getBlock(block_number).timestamp
