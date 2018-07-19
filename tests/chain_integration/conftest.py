import json
import os
import sys
import subprocess

import pytest
import gevent
from web3 import Web3, HTTPProvider
from web3.utils.transactions import wait_for_transaction_receipt
from eth_utils import to_checksum_address
from tlcontracts.deploy import deploy_networks, deploy_network, get_project

from relay.blockchain.currency_network_proxy import CurrencyNetworkProxy


NETWORKS = [('Fugger', 'FUG', 2), ('Hours', 'HOU', 2), ('Testcoin', 'T', 6)]


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
    accounts = web3.personal.listAccounts[0:5]
    assert len(accounts) == 5
    return [to_checksum_address(account) for account in accounts]


class CurrencyNetworkProxy(CurrencyNetworkProxy):

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

    def update_trustline(self, from_, to, creditline_given, creditline_received):
        txid = self._proxy.transact({"from": from_}).updateTrustline(to, creditline_given, creditline_received)
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


def deploy_test_network():
    project = get_project()
    with project.get_chain('testrpclocal') as chain:
        return deploy_network(chain, 'Trustlines', 'T', 6)


def deploy_test_networks():
    project = get_project()
    with project.get_chain('testrpclocal') as chain:
        return deploy_networks(chain, NETWORKS)


@pytest.fixture(scope='session')
def contracts():
    with open(os.path.join(sys.prefix, 'trustlines-contracts', 'build', 'contracts.json')) as data_file:
        return json.load(data_file)


@pytest.fixture(scope='session')
def currency_network_abi(contracts):
    return contracts['CurrencyNetwork']['abi']


@pytest.fixture(scope='session')
def exchange_abi(contracts):
    return contracts['Exchange']['abi']


@pytest.fixture(scope='session')
def token_abi(contracts):
    return contracts['Token']['abi']


@pytest.fixture(scope='session')
def testnetwork1_address():
    return deploy_test_network().address


@pytest.fixture(scope='session')
def testnetwork2_address():
    return deploy_test_network().address


@pytest.fixture()
def testnetwork3_address():
    return deploy_test_network().address


@pytest.fixture()
def testnetworks(accounts):
    maker, taker, *rest = accounts
    currency_network_contracts, exchange_contract, unw_eth_contract = deploy_test_networks()

    unw_eth_contract.transact({'from': taker, 'value': 200}).deposit()

    currency_network = currency_network_contracts[0]
    currency_network.transact({'from': taker}).updateCreditline(maker, 300)
    currency_network.transact({'from': maker}).acceptCreditline(taker, 300)

    return currency_network_contracts, exchange_contract, unw_eth_contract


@pytest.fixture()
def exchange_address(testnetworks):
    return testnetworks[1].address


@pytest.fixture()
def unw_eth_address(testnetworks):
    return testnetworks[2].address


@pytest.fixture()
def network_addresses_with_exchange(testnetworks):
    return [network.address for network in testnetworks[0]]


@pytest.fixture(scope='session')
def currency_network(web3, currency_network_abi, testnetwork1_address):
    """this currency network is not reset for speed reasons,
       only use it for constant tests"""
    currency_network = CurrencyNetworkProxy(web3, currency_network_abi, testnetwork1_address)
    return currency_network


@pytest.fixture(scope='session')
def currency_network_with_trustlines(web3, currency_network_abi, testnetwork2_address, trustlines):
    """this currency network is not reset for speed reasons,
        only use it for constant tests"""
    currency_network = CurrencyNetworkProxy(web3, currency_network_abi, testnetwork2_address)

    currency_network.setup_trustlines(trustlines)

    return currency_network


@pytest.fixture()
def fresh_currency_network(web3, currency_network_abi, testnetwork3_address, trustlines):
    """this currency network is reset on every use which is very slow,
            only use it if you need it"""
    currency_network = CurrencyNetworkProxy(web3, currency_network_abi, testnetwork3_address)

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


@pytest.fixture()
def address_oracle(testnetworks):

    class AddressOracle():

        def is_currency_network(self, address):
            return address in [network.address for network in testnetworks[0]]

        def is_trusted_token(self, address):
            print(address)
            print(testnetworks[2].address)
            return address == testnetworks[2].address

    return AddressOracle()
