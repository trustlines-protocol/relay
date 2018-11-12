import os
import logging
from collections import namedtuple

from relay.logger import get_logger
from relay.concurrency_utils import synchronized


TxInfos = namedtuple('TxInfos', 'balance, nonce, gas_price')


logger = get_logger('node', logging.DEBUG)


class Node:

    def __init__(self, web3, is_parity=True):
        self._web3 = web3
        self.is_parity = is_parity
        if is_parity:
            logger.info('Assuming connected to parity node: Enabling parity-only rpc methods.')

        # the instant seal engine used in the e2e tests does not work properly,
        # when we we relay multiple transactions at the same time.
        # It looks like parity just does not create a new block for the
        # second transaction it sees. When we make the relay_tx method synchronized,
        # transactions will not end up at parity at the same time.
        # This makes it possible to run the end2end tests.
        # Somehow this only became an issue after the upgrade to web3 4.x
        # Opened an upstream issue https://github.com/paritytech/parity-ethereum/issues/9660
        if os.environ.get("TRUSTLINES_SYNC_TX_RELAY", "") == "1":
            logger.warning("synchronizing tx relaying because TRUSTLINES_SYNC_TX_RELAY is set")
            self._send_tx = synchronized(self._web3.eth.sendRawTransaction)
        else:
            self._send_tx = self._web3.eth.sendRawTransaction

    def relay_tx(self, rawtxn):
        return self._send_tx(rawtxn)

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
            }).hex()
        else:
            return None

    def get_block_timestamp(self, block_number):
        return self._web3.eth.getBlock(block_number).timestamp
