from collections import namedtuple
from typing import List

from deploy_tools.deploy import TransactionFailed
from tldeploy.identity import (
    Delegate as DelegateImplementation,
    MetaTransaction,
    UnexpectedIdentityContractException,
    deploy_proxied_identity,
)

DelegationFees = namedtuple("DelegationFees", ["value", "currency_network"])


class Delegate:
    def __init__(
        self,
        web3,
        node_address,
        identity_contract_abi,
        known_factories,
        delegation_fees,
    ):
        self._web3 = web3

        self.delegate = DelegateImplementation(
            node_address, web3=web3, identity_contract_abi=identity_contract_abi
        )
        self.known_factories = known_factories
        self.delegation_fees = delegation_fees

    def send_signed_meta_transaction(self, signed_meta_transaction: MetaTransaction):
        self.validate_meta_transaction_fees(signed_meta_transaction)
        try:
            valid = self.delegate.validate_meta_transaction(signed_meta_transaction)
        except UnexpectedIdentityContractException as e:
            raise InvalidIdentityContractException(e)

        if valid:
            return self.delegate.send_signed_meta_transaction(signed_meta_transaction)
        else:
            raise InvalidMetaTransactionException

    def deploy_identity(self, factory_address, implementation_address, signature):
        if factory_address not in self.known_factories:
            raise UnknownIdentityFactoryException(factory_address)
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

    def calculate_fees_for_meta_transaction(
        self, meta_transaction: MetaTransaction
    ) -> List[DelegationFees]:
        try:
            valid = self.delegate.validate_nonce(meta_transaction)
        except UnexpectedIdentityContractException as e:
            raise InvalidIdentityContractException(e)

        if valid:
            return self.delegation_fees
        else:
            raise InvalidMetaTransactionException

    def validate_meta_transaction_fees(self, meta_transaction: MetaTransaction):
        fees_estimations = self.calculate_fees_for_meta_transaction(meta_transaction)
        if not fees_estimations:
            return
        for fees_estimation in fees_estimations:
            if fees_estimation.value == 0:
                return
            if (
                fees_estimation.currency_network
                == meta_transaction.currency_network_of_fees
                and fees_estimation.value <= meta_transaction.fees
            ):
                return

        raise InvalidDelegationFeesException()


class InvalidIdentityContractException(Exception):
    pass


class InvalidMetaTransactionException(Exception):
    pass


class IdentityDeploymentFailedException(Exception):
    pass


class UnknownIdentityFactoryException(Exception):
    pass


class InvalidDelegationFeesException(Exception):
    pass
