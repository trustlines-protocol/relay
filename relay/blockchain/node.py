from collections import namedtuple


TxInfos = namedtuple('TxInfos', 'balance, nonce, gas_price')


class Node:

    def __init__(self, web3):
        self._web3 = web3

    def relay_tx(self, rawtxn):
        return self._web3.eth.sendRawTransaction(rawtxn)

    def transaction_receipt(self, txn_hash):
        return self._web3.eth.getTransactionReceipt(txn_hash)

    def get_tx_infos(self, user_address):
        return TxInfos(balance=self._web3.eth.getBalance(user_address),
                       nonce=self._web3.eth.getTransactionCount(user_address),
                       gas_price=self._web3.eth.gasPrice)

    @property
    def blocknumber(self):
        return self._web3.eth.blockNumber

    def balance(self, address):
        wei = self._web3.eth.getBalance(address)
        return str(self._web3.fromWei(wei, 'ether'))

    def send_ether(self, address):
        if self._web3.eth.getBalance(address) == 0:
            return self._web3.eth.sendTransaction({
                'from': self._web3.eth.coinbase,
                'to': address,
                'value': 1000000000000000000
            })
        else:
            return None

    def get_block_timestamp(self, block_number):
        return self._web3.eth.getBlock(block_number).timestamp
