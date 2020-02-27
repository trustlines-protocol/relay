from enum import Enum
from typing import List

import attr
from deploy_tools.deploy import TransactionFailed
from tldeploy.identity import (
    Delegate as DelegateImplementation,
    MetaTransaction,
    UnexpectedIdentityContractException,
    deploy_proxied_identity,
)

ZERO_ADDRESS = "0x" + "0" * 40


class GasPriceMethod(Enum):
    RPC = "rpc"
    FIXED = "fixed"
    BOUND = "bound"


@attr.s
class DelegationFees:
    currency_network_of_fees = attr.ib()
    fee_recipient = attr.ib(default=ZERO_ADDRESS)
    base_fee = attr.ib(default=0)
    gas_price = attr.ib(default=0)


class Delegate:
    def __init__(
        self,
        web3,
        node_address,
        identity_contract_abi,
        known_factories,
        delegation_fees,
        config,
    ):
        self._web3 = web3

        self.delegate = DelegateImplementation(
            node_address, web3=web3, identity_contract_abi=identity_contract_abi
        )
        self.known_factories = known_factories
        self.delegation_fees = delegation_fees
        self.config = config

    def send_signed_meta_transaction(self, signed_meta_transaction: MetaTransaction):
        self.raise_on_invalid_signed_meta_transaction(signed_meta_transaction)
        self.validate_meta_transaction_fees(signed_meta_transaction)

        transaction_options = {
            "gas": self._calculate_gas_limit(meta_transaction=signed_meta_transaction),
            "gasPrice": self._calculate_gas_price(
                meta_transaction=signed_meta_transaction
            ),
        }

        return self.delegate.send_signed_meta_transaction(
            signed_meta_transaction, transaction_options=transaction_options
        )

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
        self.raise_on_invalid_meta_transaction(meta_transaction)
        return self._calculate_fees_for_meta_transaction(meta_transaction)

    def _calculate_fees_for_meta_transaction(
        self, meta_transaction: MetaTransaction
    ) -> List[DelegationFees]:
        """This function should use the information of a meta-transaction
        to evaluate the fees the delegate would want to receive to pay for it"""
        return self.delegation_fees

    def validate_meta_transaction_fees(self, meta_transaction: MetaTransaction):
        fees_estimations = self._calculate_fees_for_meta_transaction(meta_transaction)
        if not fees_estimations:
            return
        for fees_estimation in fees_estimations:
            if fees_estimation.base_fee == 0 and fees_estimation.gas_price == 0:
                return
            if (
                fees_estimation.currency_network_of_fees
                == meta_transaction.currency_network_of_fees
                and fees_estimation.base_fee <= meta_transaction.base_fee
                and fees_estimation.gas_price <= meta_transaction.gas_price
            ):
                return

        raise InvalidDelegationFeesException()

    def raise_on_invalid_meta_transaction(self, meta_transaction: MetaTransaction):
        if not self.delegate.validate_time_limit(meta_transaction):
            raise InvalidTimeLimit
        if not self.delegate.validate_chain_id(meta_transaction):
            raise InvalidChainId
        if not self.delegate.validate_nonce(meta_transaction):
            raise InvalidNonceHashPair

    def raise_on_invalid_signed_meta_transaction(
        self, signed_meta_transaction: MetaTransaction
    ):
        self.raise_on_invalid_meta_transaction(signed_meta_transaction)
        if not self.delegate.validate_signature(signed_meta_transaction):
            raise InvalidSignature

    def _calculate_gas_price(self, meta_transaction: MetaTransaction):
        method = self.config["gas_price_method"]
        if method == GasPriceMethod.FIXED:
            return self.config["gas_price"]
        elif method == GasPriceMethod.BOUND:
            return min(
                max(self._fetch_rpc_gas_price(), self.config["min_gas_price"]),
                self.config["max_gas_price"],
            )
        elif method == GasPriceMethod.RPC:
            return self._fetch_rpc_gas_price()
        else:
            raise ValueError(f"Unknown method: {method}")

    def _calculate_gas_limit(self, meta_transaction: MetaTransaction):
        return self.config["max_gas_limit"]

    def _fetch_rpc_gas_price(self) -> int:
        raw_value = self._web3.manager.request_blocking("eth_gasPrice", [])
        if isinstance(raw_value, int):
            return raw_value
        elif isinstance(raw_value, str):
            return int(raw_value, 16)
        else:
            raise RuntimeError(f"Unexpected rpc gas price value: {raw_value}")


class InvalidIdentityContractException(Exception):
    pass


class InvalidMetaTransactionException(Exception):
    pass


class InvalidTimeLimit(InvalidMetaTransactionException):
    pass


class InvalidChainId(InvalidMetaTransactionException):
    pass


class InvalidNonceHashPair(InvalidMetaTransactionException):
    pass


class InvalidSignature(InvalidMetaTransactionException):
    pass


class IdentityDeploymentFailedException(Exception):
    pass


class UnknownIdentityFactoryException(Exception):
    pass


class InvalidDelegationFeesException(Exception):
    pass
