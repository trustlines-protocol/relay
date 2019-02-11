#! pytest
import pytest
from tldeploy.identity import MetaTransaction, Identity
from tldeploy.core import deploy_identity

from relay.blockchain.delegate import Delegate


@pytest.fixture(scope='session')
def delegate_address(web3):
    return web3.eth.coinbase


@pytest.fixture(scope='session')
def delegate(web3, delegate_address, contracts):

    identity_contract_abi = contracts['Identity']['abi']

    return Delegate(web3, delegate_address, identity_contract_abi)


@pytest.fixture(scope='session')
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope='session')
def owner_key(account_keys):
    return account_keys[0]


@pytest.fixture(scope='session')
def identity_contract(web3, owner):

    identity_contract = deploy_identity(web3, owner)
    web3.eth.sendTransaction({'to': identity_contract.address, 'from': owner, 'value': 1000000})

    return identity_contract


@pytest.fixture(scope='session')
def identity(identity_contract, owner_key):
    return Identity(contract=identity_contract, owner_private_key=owner_key)


def meta_transaction_for_currency_network_transfer(currency_network, identity, source, destination):

    trustlines = [(source, destination, 100, 100)]
    currency_network.setup_trustlines(trustlines)
    meta_transaction = currency_network.transfer_meta_transaction(destination, 100, 0, [destination])
    meta_transaction = identity.filled_and_signed_meta_transaction(meta_transaction)

    return meta_transaction


def test_delegate_meta_transaction(delegate, web3, accounts, account_keys):
    """"
    Tests that a transaction is sent by the delegate upon receiving a meta-transaction.
    This tests might need to be modified for a correct meta-transaction
    once verification of meta-transaction is implemented
    """

    meta_transaction_destinary = accounts[1]

    meta_transaction = MetaTransaction(
        from_=meta_transaction_destinary,
        to=accounts[2],
        value=123,
        data=(1234).to_bytes(10, byteorder='big'),
        nonce=1,
        extra_data=(123456789).to_bytes(10, byteorder='big'),
    )

    signed_meta_transaction = meta_transaction.signed(account_keys[1])

    tx_hash = delegate.send_signed_meta_transaction(signed_meta_transaction)
    tx = web3.eth.getTransaction(tx_hash)

    assert tx['from'] == web3.eth.coinbase
    assert tx['to'] == meta_transaction_destinary


def test_delegated_transaction_trustlines_flow(currency_network, identity, delegate, accounts):
    """"
    Tests that the relaying of the metatransaction by the relay server works on a currency network contract
    """

    source = identity.address
    destination = accounts[3]

    meta_transaction = meta_transaction_for_currency_network_transfer(
        currency_network,
        identity,
        source,
        destination,
    )

    delegate.send_signed_meta_transaction(meta_transaction)

    assert currency_network.get_balance(source, destination) == -100


def test_deploy_identity(currency_network, web3, delegate, accounts, owner, owner_key,):
    """
    Tests that the deployment of an identity contract by the relay server delegate works
    by using it to execute a meta-transaction
    """

    identity_contract = delegate.deploy_identity(web3, owner)
    identity = Identity(contract=identity_contract, owner_private_key=owner_key)

    source = identity_contract.address
    destination = accounts[3]

    meta_transaction = meta_transaction_for_currency_network_transfer(
        currency_network,
        identity,
        source,
        destination,
    )

    assert identity_contract.functions.lastNonce().call() == 0
    delegate.send_signed_meta_transaction(meta_transaction)
    assert identity_contract.functions.lastNonce().call() == 1
    assert currency_network.get_balance(source, destination) == -100
