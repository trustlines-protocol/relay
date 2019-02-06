#! pytest
import pytest
from eth_tester.exceptions import TransactionFailed
from tldeploy.identity import MetaTransaction

from relay.blockchain.delegate import Delegate
from relay.relay import TrustlinesRelay

@pytest.fixture(scope='session')
def delegate(web3):

    address = web3.eth.coinbase
    trustlines_relay = TrustlinesRelay()
    trustlines_relay._load_contracts()
    identity_contract_abi = trustlines_relay.contracts['Identity']['abi']

    return Delegate(web3, address, identity_contract_abi)


def test_delegate_metatransaction(delegate, web3, accounts, account_keys):

    metatransaction = MetaTransaction(
        from_=accounts[1],
        to=accounts[2],
        value=123,
        data=(1234).to_bytes(10, byteorder='big'),
        nonce=1,
        extra_data=(123456789).to_bytes(10, byteorder='big'),
    )

    signed_metatransaction = metatransaction.signed(account_keys[1])

    tx_hash = delegate.send_signed_meta_transaction(signed_metatransaction)
    tx = web3.eth.getTransaction(tx_hash)

    assert tx['from'] == web3.eth.coinbase
