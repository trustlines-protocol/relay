import pytest

from relay.blockchain.node import Node, TransactionStatus


@pytest.fixture(scope="session")
def node(web3):
    return Node(web3)


def test_tx_status_success(web3, node, accounts):
    tx_hash = web3.eth.sendTransaction(
        {"from": accounts[0], "to": accounts[1], "value": 10}
    )
    assert node.get_transaction_status(tx_hash) == TransactionStatus.SUCCESS


def test_tx_status_not_found(node):
    unfindable_hash = "0x" + "01" * 32
    assert node.get_transaction_status(unfindable_hash) == TransactionStatus.NOT_FOUND


def test_tx_status_pending(web3, node, accounts, chain):
    chain.disable_auto_mine_transactions()

    tx_hash = web3.eth.sendTransaction(
        {"from": accounts[0], "to": accounts[1], "value": 10}
    )
    assert node.get_transaction_status(tx_hash) == TransactionStatus.PENDING
    chain.enable_auto_mine_transactions()
