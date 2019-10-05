from tldeploy.identity import (
    MetaTransaction,
    Delegate as DelegateImplementation,
    UnexpectedIdentityContractException,
)
from tldeploy.identity import deploy_proxied_identity
from deploy_tools.deploy import TransactionFailed


class Delegate:
    def __init__(self, web3, node_address, identity_contract_abi):

        self._web3 = web3

        self.delegate = DelegateImplementation(
            node_address, web3=web3, identity_contract_abi=identity_contract_abi
        )

    def send_signed_meta_transaction(self, signed_meta_transaction: MetaTransaction):
        try:
            valid = self.delegate.validate_meta_transaction(signed_meta_transaction)
        except UnexpectedIdentityContractException as e:
            raise InvalidIdentityContractException(e)

        if valid:
            return self.delegate.send_signed_meta_transaction(signed_meta_transaction)
        else:
            raise InvalidMetaTransactionException

    def deploy_identity(self, factory_address, implementation_address, signature):
        try:
            # when getting an address via contract.address, the address might not be a checksummed address
            return self._web3.toChecksumAddress(
                deploy_proxied_identity(
                    self._web3, factory_address, implementation_address, signature
                ).address
            )
        except TransactionFailed:
            raise IdentityDeploymentFailedException

    def calc_next_nonce(self, identity_address: str):
        try:
            return self.delegate.get_next_nonce(identity_address)
        except UnexpectedIdentityContractException:
            raise InvalidIdentityContractException


class InvalidIdentityContractException(Exception):
    pass


class InvalidMetaTransactionException(Exception):
    pass


class IdentityDeploymentFailedException(Exception):
    pass
