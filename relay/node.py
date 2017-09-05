
class Node:

    def __init__(self, web3):
        self._web3 = web3

    def relay_tx(self, rawtxn):
        return self._web3.eth.sendRawTransaction(rawtxn)

    def transaction_receipt(self, txn_hash):
        return self._web3.eth.getTransactionReceipt(txn_hash)

    def get_tx_infos(self, user_address):
        return {'balance': self._web3.eth.getBalance(user_address),
                'nonce': self._web3.eth.getTransactionCount(user_address),
                'gasPrice': self._web3.eth.gasPrice}

    @property
    def blocknumber(self):
        return self._web3.eth.blockNumber

    def balance(self, address):
        wei = int(self._web3.eth.getBalance(address), 0)
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

    def get_block_time(self, block_number):
        return self._web3.eth.getBlock(block_number).timestamp

    def get_block_status(self, block_number=None):
        current_block_number = self._web3.eth.blockNumber
        if block_number is None:
            return 'sent'
        elif (current_block_number - block_number) <  5:
            return 'pending'
        else:
            return 'confirmed'
