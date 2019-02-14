from tldeploy.identity import MetaTransaction, Delegator, UnexpectedIdentityContractException
from tldeploy.core import deploy_identity


class Delegate:

    def __init__(self, web3,  node_address, identity_contract_abi):

        self._web3 = web3

        self.delegator = Delegator(
            node_address,
            web3=web3,
            identity_contract_abi=identity_contract_abi
        )

    def send_signed_meta_transaction(self, signed_meta_transaction: MetaTransaction):
        try:
            valid = self.delegator.validate_meta_transaction(signed_meta_transaction)
        except UnexpectedIdentityContractException as e:
            raise InvalidIdentityContractException(e)

        if valid:
            return self.delegator.send_signed_meta_transaction(signed_meta_transaction)
        else:
            raise InvalidMetaTransactionException

    def deploy_identity(self, owner_address: str) -> str:
        return deploy_identity(self._web3, owner_address).address

    def calc_next_nonce(self, identity_address: str):
        try:
            return self.delegator.get_next_nonce(identity_address)
        except UnexpectedIdentityContractException:
            raise InvalidIdentityContractException


class InvalidIdentityContractException(Exception):
    pass


class InvalidMetaTransactionException(Exception):
    pass
