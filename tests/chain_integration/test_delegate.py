#! pytest
import attr
import pytest
from eth_utils import to_checksum_address
from tldeploy.identity import (
    Identity,
    MetaTransaction,
    UnexpectedIdentityContractException,
    deploy_identity_implementation,
    deploy_identity_proxy_factory,
    deploy_proxied_identity,
)
from web3 import Web3

from relay.blockchain.delegate import (
    Delegate,
    DelegationFees,
    GasPriceMethod,
    InvalidDelegationFeesException,
    InvalidMetaTransactionException,
)


@pytest.fixture(scope="session")
def delegate_address(web3):
    return web3.eth.coinbase


@pytest.fixture(scope="session")
def delegate_config():
    return {
        "gas_price_method": GasPriceMethod.FIXED,
        "gas_price": 2_000_000_000,
        "max_gas_limit": 1_000_000,
    }


@pytest.fixture(scope="session")
def delegate(
    web3, delegate_address, contracts, proxy_factory, currency_network, delegate_config
):
    identity_contract_abi = contracts["Identity"]["abi"]
    base_fee = 0
    return Delegate(
        web3,
        delegate_address,
        identity_contract_abi,
        [proxy_factory.address],
        delegation_fees=[
            DelegationFees(
                base_fee=base_fee, currency_network_of_fees=currency_network.address
            )
        ],
        config=delegate_config,
    )


@pytest.fixture(scope="session")
def delegate_with_one_fees(
    web3, delegate_address, contracts, proxy_factory, currency_network, delegate_config
):
    identity_contract_abi = contracts["Identity"]["abi"]
    base_fee = 1
    return Delegate(
        web3,
        delegate_address,
        identity_contract_abi,
        [proxy_factory.address],
        delegation_fees=[
            DelegationFees(
                base_fee=base_fee, currency_network_of_fees=currency_network.address
            )
        ],
        config=delegate_config,
    )


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def owner_key(account_keys):
    return account_keys[0]


@pytest.fixture(scope="session")
def proxy_factory(web3):

    return deploy_identity_proxy_factory(web3=web3)


@pytest.fixture(scope="session")
def identity_implementation(web3):

    return deploy_identity_implementation(web3=web3)


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
        {"to": identity_contract.address, "from": owner, "value": 1_000_000}
    )

    return identity_contract


@pytest.fixture()
def identity(identity_contract, owner_key):
    return Identity(contract=identity_contract, owner_private_key=owner_key)


@pytest.fixture()
def chain_id(web3):
    return int(web3.eth.chainId)


@pytest.fixture()
def build_meta_transaction(chain_id):
    """Adds chain_id and build meta-tx from given args"""

    def f(*args, **kwargs):
        return MetaTransaction(*args, **kwargs, chain_id=chain_id)

    return f


@pytest.fixture()
def signed_meta_transaction(identity, owner_key, accounts, build_meta_transaction):
    meta_transaction = build_meta_transaction(
        from_=identity.address,
        to=accounts[2],
        value=123,
        data=(1234).to_bytes(10, byteorder="big"),
        nonce=1,
    )

    return meta_transaction.signed(owner_key)


def meta_transaction_for_currency_network_transfer(
    currency_network, identity, source, destination
):

    trustlines = [(source, destination, 100, 100)]
    currency_network.setup_trustlines(trustlines)
    meta_transaction = currency_network.transfer_meta_transaction(
        100, 0, [source, destination]
    )
    meta_transaction = identity.filled_and_signed_meta_transaction(meta_transaction)

    return meta_transaction


def test_delegate_meta_transaction(delegate, identity, web3, signed_meta_transaction):
    """"
    Tests that a transaction is sent by the delegate upon receiving a meta-transaction.
    """

    tx_hash = delegate.send_signed_meta_transaction(signed_meta_transaction)
    tx = web3.eth.getTransaction(tx_hash)

    assert tx["from"] == web3.eth.coinbase
    assert to_checksum_address(tx["to"]) == identity.address


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
        100, 0, [identity_contract_address, destination]
    )
    signed_meta_transaction = attr.evolve(
        meta_transaction, from_=identity_contract_address, nonce=0
    ).signed(owner_key)

    currency_network.setup_trustlines(
        [(identity_contract_address, destination, 100, 100)]
    )
    delegate.send_signed_meta_transaction(signed_meta_transaction)
    assert currency_network.get_balance(identity_contract_address, destination) == -100


def test_next_nonce(
    delegate, identity_contract, accounts, owner_key, build_meta_transaction
):

    source = identity_contract.address
    destination = accounts[3]

    meta_transaction = build_meta_transaction(
        from_=source, to=destination, value=123, nonce=delegate.calc_next_nonce(source)
    )
    signed_meta_transaction = meta_transaction.signed(owner_key)

    assert delegate.calc_next_nonce(source) == 1
    delegate.send_signed_meta_transaction(signed_meta_transaction)
    assert delegate.calc_next_nonce(source) == 2

    meta_transaction = build_meta_transaction(
        from_=source, to=destination, value=123, nonce=delegate.calc_next_nonce(source)
    )
    signed_meta_transaction = meta_transaction.signed(owner_key)

    assert delegate.calc_next_nonce(source) == 2
    delegate.send_signed_meta_transaction(signed_meta_transaction)
    assert delegate.calc_next_nonce(source) == 3


def test_delegated_transaction_invalid_signature(
    identity, delegate, accounts, account_keys, build_meta_transaction
):
    to = accounts[2]
    value = 1000

    meta_transaction = build_meta_transaction(
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
    delegate, accounts, account_keys, build_meta_transaction
):
    from_ = accounts[1]
    to = accounts[2]
    value = 1000

    meta_transaction = build_meta_transaction(
        from_=from_, to=to, value=value, nonce=0
    ).signed(account_keys[3])

    with pytest.raises(UnexpectedIdentityContractException):
        delegate.send_signed_meta_transaction(meta_transaction)


def test_meta_transaction_fees_valid(
    delegate_with_one_fees, signed_meta_transaction, owner_key
):
    """
    Check that no exception is raised when validating a valid meta_transaction
    """

    delegation_fees = delegate_with_one_fees.calculate_fees_for_meta_transaction(
        signed_meta_transaction
    )[0]
    meta_transaction_with_fees = attr.evolve(
        signed_meta_transaction,
        base_fee=delegation_fees.base_fee,
        currency_network_of_fees=delegation_fees.currency_network_of_fees,
    )
    signed_meta_transaction_with_fees = meta_transaction_with_fees.signed(owner_key)
    delegate_with_one_fees.validate_meta_transaction_fees(
        signed_meta_transaction_with_fees
    )


def test_meta_transaction_fees_invalid_value(
    delegate_with_one_fees, signed_meta_transaction, owner_key
):
    """
    Check that an exception is raised when validating an invalid meta_transaction
    """

    delegation_fees = delegate_with_one_fees.calculate_fees_for_meta_transaction(
        signed_meta_transaction
    )[0]

    wrong_fees_value = 0
    assert delegation_fees.base_fee >= wrong_fees_value

    meta_transaction_with_fees = attr.evolve(
        signed_meta_transaction,
        base_fee=wrong_fees_value,
        currency_network_of_fees=delegation_fees.currency_network_of_fees,
    )
    signed_meta_transaction_with_fees = meta_transaction_with_fees.signed(owner_key)

    with pytest.raises(InvalidDelegationFeesException):
        delegate_with_one_fees.validate_meta_transaction_fees(
            signed_meta_transaction_with_fees
        )


def test_meta_transaction_fees_invalid_network(
    delegate_with_one_fees, signed_meta_transaction, owner_key
):
    """
    Check that an exception is raised when validating an invalid meta_transaction
    """

    delegation_fees = delegate_with_one_fees.calculate_fees_for_meta_transaction(
        signed_meta_transaction
    )[0]

    wrong_network = signed_meta_transaction.from_
    assert delegation_fees.currency_network_of_fees != wrong_network

    meta_transaction_with_fees = attr.evolve(
        signed_meta_transaction,
        base_fee=delegation_fees.base_fee,
        currency_network_of_fees=wrong_network,
    )
    signed_meta_transaction_with_fees = meta_transaction_with_fees.signed(owner_key)

    with pytest.raises(InvalidDelegationFeesException):
        delegate_with_one_fees.validate_meta_transaction_fees(
            signed_meta_transaction_with_fees
        )


@pytest.mark.parametrize(
    "gas_price_config, gas_price",
    [
        (
            {"gas_price_method": GasPriceMethod.FIXED, "gas_price": 2_000_000_000},
            2_000_000_000,
        ),
        # Assumes the default gas price of the chain is 1
        ({"gas_price_method": GasPriceMethod.RPC}, 1),
        (
            {
                "gas_price_method": GasPriceMethod.BOUND,
                "min_gas_price": 1_000_000_000,
                "max_gas_price": 5_000_000_000,
            },
            1_000_000_000,
        ),
        (
            {
                "gas_price_method": GasPriceMethod.BOUND,
                "min_gas_price": 0,
                "max_gas_price": 0,
            },
            0,
        ),
    ],
)
def test_gas_pricing(delegate, delegate_config, gas_price_config, gas_price):
    config = dict(**delegate_config)
    config.update(gas_price_config)

    delegate.config = config

    assert delegate._calculate_gas_price(MetaTransaction()) == gas_price
