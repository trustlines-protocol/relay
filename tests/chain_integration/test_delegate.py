#! pytest
import attr
import pytest
from hexbytes import HexBytes
from tldeploy.identity import (
    Identity,
    MetaTransaction,
    deploy_identity_implementation,
    deploy_identity_proxy_factory,
    deploy_proxied_identity,
)
from web3 import Web3

from relay.blockchain.delegate import (
    Delegate,
    InvalidIdentityContractException,
    InvalidMetaTransactionException,
)


@pytest.fixture(scope="session")
def delegate_address(web3):
    return web3.eth.coinbase


@pytest.fixture(scope="session")
def delegate(web3, delegate_address, contracts, proxy_factory):
    identity_contract_abi = contracts["Identity"]["abi"]
    return Delegate(
        web3, delegate_address, identity_contract_abi, [proxy_factory.address]
    )


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def owner_key(account_keys):
    return account_keys[0]


@pytest.fixture(scope="session")
def proxy_factory(web3):

    return deploy_identity_proxy_factory(web3)


@pytest.fixture(scope="session")
def identity_implementation(web3):

    return deploy_identity_implementation(web3)


@pytest.fixture(scope="session")
def signature_of_owner_on_implementation(
    owner_key, identity_implementation, proxy_factory
):
    abi_types = ["bytes1", "bytes1", "address", "address"]
    to_hash = ["0x19", "0x00", proxy_factory.address, identity_implementation.address]
    to_sign = Web3.solidityKeccak(abi_types, to_hash)
    return owner_key.sign_msg_hash(to_sign).to_bytes()


@pytest.fixture()
def identity_contract(
    web3,
    proxy_factory,
    identity_implementation,
    signature_of_owner_on_implementation,
    owner,
):
    identity_contract = deploy_proxied_identity(
        web3,
        proxy_factory.address,
        identity_implementation.address,
        signature_of_owner_on_implementation,
    )
    web3.eth.sendTransaction(
        {"to": identity_contract.address, "from": owner, "value": 1000000}
    )

    return identity_contract


@pytest.fixture()
def identity(identity_contract, owner_key):
    return Identity(contract=identity_contract, owner_private_key=owner_key)


def meta_transaction_for_currency_network_transfer(
    currency_network, identity, source, destination
):

    trustlines = [(source, destination, 100, 100)]
    currency_network.setup_trustlines(trustlines)
    meta_transaction = currency_network.transfer_meta_transaction(
        destination, 100, 0, [destination]
    )
    meta_transaction = identity.filled_and_signed_meta_transaction(meta_transaction)

    return meta_transaction


def test_delegate_meta_transaction(delegate, identity, web3, accounts, owner_key):
    """"
    Tests that a transaction is sent by the delegate upon receiving a meta-transaction.
    """

    meta_transaction = MetaTransaction(
        from_=identity.address,
        to=accounts[2],
        value=123,
        data=(1234).to_bytes(10, byteorder="big"),
        nonce=1,
        extra_data=(123456789).to_bytes(10, byteorder="big"),
    )

    signed_meta_transaction = meta_transaction.signed(owner_key)

    tx_hash = delegate.send_signed_meta_transaction(signed_meta_transaction)
    tx = web3.eth.getTransaction(tx_hash)

    assert tx["from"] == web3.eth.coinbase
    assert HexBytes(tx["to"]) == identity.address


def test_delegated_transaction_trustlines_flow(
    currency_network, identity, delegate, accounts
):
    """"
    Tests that the relaying of the metatransaction by the relay server works on a currency network contract
    """

    source = identity.address
    destination = accounts[3]

    meta_transaction = meta_transaction_for_currency_network_transfer(
        currency_network, identity, source, destination
    )

    delegate.send_signed_meta_transaction(meta_transaction)

    assert currency_network.get_balance(source, destination) == -100


def test_deploy_identity(
    currency_network,
    delegate,
    accounts,
    proxy_factory,
    owner_key,
    identity_implementation,
    signature_of_owner_on_implementation,
):
    """
    Tests that the deployment of an identity contract by the relay server delegate works
    by using it to execute a meta-transaction
    """

    identity_contract_address = delegate.deploy_identity(
        proxy_factory.address,
        identity_implementation.address,
        signature_of_owner_on_implementation,
    )

    destination = accounts[3]

    meta_transaction = currency_network.transfer_meta_transaction(
        destination, 100, 0, [destination]
    )
    signed_meta_transaction = attr.evolve(
        meta_transaction, from_=identity_contract_address, nonce=0
    ).signed(owner_key)

    currency_network.setup_trustlines(
        [(identity_contract_address, destination, 100, 100)]
    )
    delegate.send_signed_meta_transaction(signed_meta_transaction)
    assert currency_network.get_balance(identity_contract_address, destination) == -100


def test_next_nonce(delegate, identity_contract, accounts, owner_key):

    source = identity_contract.address
    destination = accounts[3]

    meta_transaction = MetaTransaction(
        from_=source, to=destination, value=123, nonce=delegate.calc_next_nonce(source)
    )
    signed_meta_transaction = meta_transaction.signed(owner_key)

    assert delegate.calc_next_nonce(source) == 1
    delegate.send_signed_meta_transaction(signed_meta_transaction)
    assert delegate.calc_next_nonce(source) == 2

    meta_transaction = MetaTransaction(
        from_=source, to=destination, value=123, nonce=delegate.calc_next_nonce(source)
    )
    signed_meta_transaction = meta_transaction.signed(owner_key)

    assert delegate.calc_next_nonce(source) == 2
    delegate.send_signed_meta_transaction(signed_meta_transaction)
    assert delegate.calc_next_nonce(source) == 3


def test_delegated_transaction_invalid_signature(
    identity, delegate, accounts, account_keys
):
    to = accounts[2]
    value = 1000

    meta_transaction = MetaTransaction(
        from_=identity.address, to=to, value=value, nonce=0
    ).signed(account_keys[3])

    with pytest.raises(InvalidMetaTransactionException):
        delegate.send_signed_meta_transaction(meta_transaction)


def test_delegated_transaction_invalid_nonce(identity, delegate, accounts):
    to = accounts[2]
    value = 1000

    meta_transaction1 = identity.filled_and_signed_meta_transaction(
        MetaTransaction(to=to, value=value, nonce=1)
    )
    meta_transaction2 = identity.filled_and_signed_meta_transaction(
        MetaTransaction(to=to, value=value, nonce=1)
    )

    delegate.send_signed_meta_transaction(meta_transaction1)

    with pytest.raises(InvalidMetaTransactionException):
        delegate.send_signed_meta_transaction(meta_transaction2)


def test_delegated_transaction_invalid_identity_contract(
    delegate, accounts, account_keys
):
    from_ = accounts[1]
    to = accounts[2]
    value = 1000

    meta_transaction = MetaTransaction(from_=from_, to=to, value=value, nonce=0).signed(
        account_keys[3]
    )

    with pytest.raises(InvalidIdentityContractException):
        delegate.send_signed_meta_transaction(meta_transaction)
