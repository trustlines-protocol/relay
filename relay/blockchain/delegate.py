from tldeploy.identity import MetaTransaction, Delegator
from tldeploy.core import deploy_identity


class Delegate:

    def __init__(self, web3,  node_address, identity_contract_abi):

        self.delegator = Delegator(
            node_address,
            web3=web3,
            identity_contract_abi=identity_contract_abi
        )

    def send_signed_meta_transaction(self, signed_meta_transaction: MetaTransaction,):
        return self.delegator.send_signed_meta_transaction(signed_meta_transaction)

    def deploy_identity(self, web3, owner_address):
        return deploy_identity(web3, owner_address)
