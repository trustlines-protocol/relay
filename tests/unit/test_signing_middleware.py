import attr
import eth_account
import eth_tester
import pytest
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

from relay import signing_middleware


def parity_next_nonce(make_request, w3):
    """middleware that implements parity_nextNonce

We need this, since we're talking to the eth_tester chain
"""

    def middleware(method, params):
        if method != "parity_nextNonce":
            return make_request(method, params)
        res = make_request("eth_getTransactionCount", [params[0], "pending"])
        res["result"] = hex(res["result"])
        return res

    return middleware


@pytest.fixture
def signing_account():
    """account used for signing"""
    return eth_account.Account.create()


@pytest.fixture()
def w3(signing_account):
    """
    Web3 object connected to the ethereum tester chain
    """
    chain = eth_tester.EthereumTester(eth_tester.PyEVMBackend())
    chain.send_transaction(
        {
            "from": chain.get_accounts()[0],
            "to": signing_account.address,
            "gas": 21000,
            "value": 10_000_000,
        }
    )
    w3 = Web3(EthereumTesterProvider(chain))
    w3.middleware_onion.add(parity_next_nonce)
    signing_middleware.install_signing_middleware(w3, signing_account)
    return w3


def test_eth_default_account(w3, signing_account):
    assert w3.eth.defaultAccount == signing_account.address
    with pytest.raises(RuntimeError):
        signing_middleware.install_signing_middleware(w3, signing_account)


@attr.s
class SendTxParams:
    set_from = attr.ib()
    set_nonce = attr.ib()


example_send_tx_params = [
    SendTxParams(set_nonce=False, set_from=False),
    SendTxParams(set_nonce=False, set_from=False),
    SendTxParams(set_nonce=True, set_from=False),
    SendTxParams(set_nonce=True, set_from=False),
    SendTxParams(set_nonce=True, set_from=True),
    SendTxParams(set_nonce=True, set_from=True),
    SendTxParams(set_nonce=False, set_from=True),
    SendTxParams(set_nonce=False, set_from=True),
]


def test_auto_signing(w3, signing_account):
    signing_account_balance_before = w3.eth.getBalance(
        signing_account.address, block_identifier="latest"
    )
    receiver = eth_account.Account.create().address

    value = 1
    sum_send = 0
    nonce = 0
    for params, value in zip(example_send_tx_params, range(1, 100)):
        d = {"value": value, "to": receiver}
        if params.set_nonce:
            d["nonce"] = nonce
        if params.set_from:
            d["from"] = signing_account.address
        print("send-tx:", d)
        tx_hash = w3.eth.sendTransaction(d)
        receipt = w3.eth.waitForTransactionReceipt(tx_hash)
        assert receipt.status == 1
        sum_send += value
        receiver_balance = w3.eth.getBalance(receiver, block_identifier="latest")
        assert receiver_balance == sum_send
        signing_account_balance = w3.eth.getBalance(
            signing_account.address, block_identifier="latest"
        )
        assert signing_account_balance < signing_account_balance_before - sum_send
        nonce += 1
