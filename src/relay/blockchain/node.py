import logging
import os
from collections import namedtuple

from relay.concurrency_utils import synchronized

TxInfos = namedtuple("TxInfos", "balance, nonce, gas_price")


logger = logging.getLogger("node")


class Node:
    def __init__(self, web3, *, is_parity=True, fixed_gas_price: int = None):
        """
        Abstraction to talk directly to an ethereum node
        :param web3: web3 object connected to the node
        :param is_parity: whether connected to a parity node or not. This will enable parity only rpc calls
        :param fixed_gas_price: Sets the gasprice that will be suggested to clients. If not set,
        the ethereuem node will be asked for a suggestion. This feature is useful, if the suggestion by the node will
        likely be wrong, for example because there are not so many transactions. This is also a workaround if the
        eth_gasPrice rpc call is slow
        """
        self._web3 = web3
        self.is_parity = is_parity
        self.fixed_gas_price = fixed_gas_price
        if is_parity:
            logger.info(
                "Assuming connected to parity node: Enabling parity-only rpc methods."
            )

        # the instant seal engine used in the e2e tests does not work properly,
        # when we we relay multiple transactions at the same time.
        # It looks like parity just does not create a new block for the
        # second transaction it sees. When we make the relay_tx method synchronized,
        # transactions will not end up at parity at the same time.
        # This makes it possible to run the end2end tests.
        # Somehow this only became an issue after the upgrade to web3 4.x
        # Opened an upstream issue https://github.com/paritytech/parity-ethereum/issues/9660
        if os.environ.get("TRUSTLINES_SYNC_TX_RELAY", "") == "1":
            logger.warning(
                "synchronizing tx relaying because TRUSTLINES_SYNC_TX_RELAY is set"
            )
            self._send_tx = synchronized(self._web3.eth.sendRawTransaction)
        else:
            self._send_tx = self._web3.eth.sendRawTransaction

    def relay_tx(self, rawtxn):
        return self._send_tx(rawtxn)

    def transaction_receipt(self, txn_hash):
        return self._web3.eth.getTransactionReceipt(txn_hash)

    def get_tx_infos(self, user_address, block_identifier="pending"):
        if self.is_parity and block_identifier == "pending":
            nonce = int(
                self._web3.manager.request_blocking("parity_nextNonce", [user_address]),
                16,
            )
        else:
            nonce = self._web3.eth.getTransactionCount(
                user_address, block_identifier=block_identifier
            )
        return TxInfos(
            balance=self._web3.eth.getBalance(
                user_address, block_identifier=block_identifier
            ),
            nonce=nonce,
            gas_price=self.fetch_gas_price(),
        )

    def fetch_gas_price(self) -> int:
        if self.fixed_gas_price is not None:
            return self.fixed_gas_price
        else:
            return self._web3.eth.gasPrice

    @property
    def address(self):
        return self._web3.eth.coinbase

    @property
    def blocknumber(self):
        return self._web3.eth.blockNumber

    def balance(self, address):
        return self._web3.eth.getBalance(address)

    def send_ether(self, address):
        if self._web3.eth.getBalance(address) <= 5:
            return self._web3.eth.sendTransaction(
                {
                    "from": self._web3.eth.coinbase,
                    "to": address,
                    "value": 1000000000000000000,
                }
            ).hex()
        else:
            return None

    def get_block_timestamp(self, block_number):
        return self._web3.eth.getBlock(block_number).timestamp
