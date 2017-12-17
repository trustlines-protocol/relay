import json
import os
import sys
import subprocess

import pytest
import gevent
from web3 import Web3, HTTPProvider
from web3.utils.transactions import wait_for_transaction_receipt
from eth_utils import to_checksum_address
from tlcontracts.deploy import deploy_test_network

from relay.currency_network import CurrencyNetwork


@pytest.fixture(autouse=True, scope='session')
def blockchain():
    p = subprocess.Popen('testrpc-py')
    gevent.sleep(3)  # give it some time to set up
    yield
    p.terminate()


@pytest.fixture(scope='session')
def web3():
    return Web3(HTTPProvider('http://127.0.0.1:8545'))


@pytest.fixture(scope='session')
def accounts(web3):
    # first account is coinbase and is not used for testing accounts
    accounts = web3.personal.listAccounts[1:6]
    assert len(accounts) == 5
    return [to_checksum_address(account) for account in accounts]


class CurrencyNetworkProxy(CurrencyNetwork):

    def setup_trustlines(self, trustlines):
        for (A, B, clAB, clBA) in trustlines:
            txid = self._proxy.transact().setAccount(A, B, clAB, clBA, 0, 0, 0, 0, 0, 0)
            wait_for_transaction_receipt(self._web3, txid)

    def update_creditline(self, from_, to, value):
        txid = self._proxy.transact({"from": from_}).updateCreditline(to, value)
        wait_for_transaction_receipt(self._web3, txid)

    def accept_creditline(self, from_, to, value):
        txid = self._proxy.transact({"from": from_}).acceptCreditline(to, value)
        wait_for_transaction_receipt(self._web3, txid)

    def transfer(self, from_, to, value, max_fee, path):
        txid = self._proxy.transact({"from": from_}).transfer(to, value, max_fee, path)
        wait_for_transaction_receipt(self._web3, txid)


@pytest.fixture(scope='session')
def trustlines(accounts):
    return [(accounts[0], accounts[1], 100, 150),
            (accounts[1], accounts[2], 200, 250),
            (accounts[2], accounts[3], 300, 350),
            (accounts[3], accounts[4], 400, 450),
            (accounts[0], accounts[4], 500, 550)
            ]  # (A, B, clAB, clBA)


@pytest.fixture(scope='session')
def abi():
    with open(os.path.join(sys.prefix, 'trustlines-contracts', 'build', 'contracts.json')) as data_file:
        return json.load(data_file)['CurrencyNetwork']['abi']


@pytest.fixture(scope='session')
def testnetwork1_address():
    return deploy_test_network('testrpclocal')


@pytest.fixture(scope='session')
def testnetwork2_address():
    return deploy_test_network('testrpclocal')


@pytest.fixture()
def testnetwork3_address():
    return deploy_test_network('testrpclocal')


@pytest.fixture(scope='session')
def currency_network(web3, abi, testnetwork1_address):
    """this currency network is not reset for speed reasons,
       only use it for constant tests"""
    currency_network = CurrencyNetworkProxy(web3, abi, testnetwork1_address)
    return currency_network


@pytest.fixture(scope='session')
def currency_network_with_trustlines(web3, abi, testnetwork2_address, trustlines):
    """this currency network is not reset for speed reasons,
        only use it for constant tests"""
    currency_network = CurrencyNetworkProxy(web3, abi, testnetwork2_address)

    currency_network.setup_trustlines(trustlines)

    return currency_network


@pytest.fixture()
def fresh_currency_network(web3, abi, testnetwork3_address, trustlines):
    """this currency network is reset on every use which is very slow,
            only use it if you need it"""
    currency_network = CurrencyNetworkProxy(web3, abi, testnetwork3_address)

    return currency_network


@pytest.fixture()
def currency_network_with_events(fresh_currency_network, accounts):
    fresh_currency_network.update_creditline(accounts[0], accounts[1], 25)
    fresh_currency_network.accept_creditline(accounts[1], accounts[0], 25)
    fresh_currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    fresh_currency_network.update_creditline(accounts[0], accounts[2], 25)
    fresh_currency_network.accept_creditline(accounts[2], accounts[0], 25)
    fresh_currency_network.update_creditline(accounts[0], accounts[4], 25)
    fresh_currency_network.accept_creditline(accounts[4], accounts[0], 25)

    return fresh_currency_network
