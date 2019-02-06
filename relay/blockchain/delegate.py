from tldeploy.identity import MetaTransaction, Delegator


class Delegate:

    def __init__(self, web3,  node_address, identity_contract_abi):

        self.delegator = Delegator(
            node_address,
            web3=web3,
            identity_contract_abi=identity_contract_abi
        )

    def send_signed_meta_transaction(self, signed_meta_transaction: MetaTransaction,):
        return self.delegator.send_signed_meta_transaction(signed_meta_transaction)
