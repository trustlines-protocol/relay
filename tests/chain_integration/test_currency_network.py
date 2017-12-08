import json
import os
import sys
import subprocess

import pytest
import gevent
from web3 import Web3, HTTPProvider
from web3.utils.transactions import wait_for_transaction_receipt
from tlcontracts.deploy import deploy_test_network

from relay.currency_network import CurrencyNetwork, CreditlineUpdatedEvent, CreditlineRequestEvent, TransferEvent


def context_switch():
    gevent.sleep(0.01)


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


@pytest.fixture(autouse=True, scope='session')
def blockchain():
    p = subprocess.Popen('testrpc-py')
    yield
    p.terminate()


@pytest.fixture(scope='session')
def web3():
    return Web3(HTTPProvider('http://127.0.0.1:8545'))


@pytest.fixture(scope='session')
def accounts(web3):
    # first account is coinbase and is not used for testing accounts
    accounts = web3.personal.listAccounts[1:]
    # if there are not enough accounts, create new
    for i in range(len(accounts), 5):
        web3.personal.newAccount(password='123')
    accounts = web3.personal.listAccounts[1:6]
    assert len(accounts) == 5
    return accounts


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


def test_decimals(currency_network):
    assert currency_network.decimals == 6


def test_name(currency_network):
    assert currency_network.name == 'Trustlines'


def test_symbol(currency_network):
    assert currency_network.symbol == 'T'


def test_address(currency_network, testnetwork1_address):
    assert currency_network.address == testnetwork1_address


def test_friends1(currency_network_with_trustlines, accounts):
    assert set(currency_network_with_trustlines.friends(accounts[0])) == {accounts[1], accounts[4]}


def test_friends2(currency_network_with_trustlines, accounts):
    assert set(currency_network_with_trustlines.friends(accounts[1])) == {accounts[0], accounts[2]}


def test_account1(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.account(accounts[0], accounts[1]) == [100, 150, 0, 0, 0, 0, 0, 0]


def test_account2(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.account(accounts[2], accounts[3]) == [300, 350, 0, 0, 0, 0, 0, 0]


def test_users(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.users == accounts


def test_spendable(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.spendable(accounts[1]) == 350


def test_spendable_to(currency_network_with_trustlines, accounts):
    assert currency_network_with_trustlines.spendableTo(accounts[3], accounts[4]) == 450


def test_gen_graph_representation(currency_network_with_trustlines, accounts):
    graph_representation = currency_network_with_trustlines.gen_graph_representation()

    for account in accounts:
        assert (account in graph_representation)


def test_number_of_get_events(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    assert len(currency_network.get_events(CreditlineUpdatedEvent, user_address=accounts[0])) == 3
    assert len(currency_network.get_events(CreditlineRequestEvent, user_address=accounts[0])) == 3
    assert len(currency_network.get_events(TransferEvent, user_address=accounts[0])) == 1


def test_number_of_get_all_events(currency_network_with_events, accounts):
    currency_network = currency_network_with_events
    assert len(currency_network.get_all_events(user_address=accounts[0])) == 7


def test_listen_on_creditline_update(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, value):
        events.append((from_, to, value))

    currency_network.start_listen_on_creditline(f)
    context_switch()
    currency_network.update_creditline(accounts[0], accounts[1], 25)
    currency_network.accept_creditline(accounts[1], accounts[0], 25)
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0] == (accounts[0], accounts[1], 25)


def test_listen_on_balance_update(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, value):
        events.append((from_, to, value))

    currency_network.start_listen_on_balance(f)
    context_switch()
    currency_network.update_creditline(accounts[0], accounts[1], 25)
    currency_network.accept_creditline(accounts[1], accounts[0], 25)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    gevent.sleep(1)

    assert len(events) == 1
    assert (events[0][0] == accounts[0] or events[0][0] == accounts[1])
    assert (events[0][1] == accounts[0] or events[0][1] == accounts[1])
    assert (-12 < events[0][2] < 12)  # because there might be fees


def test_listen_on_transfer(fresh_currency_network, accounts):
    currency_network = fresh_currency_network
    events = []

    def f(from_, to, value):
        events.append((from_, to, value))

    currency_network.start_listen_on_transfer(f)
    context_switch()
    currency_network.update_creditline(accounts[0], accounts[1], 25)
    currency_network.accept_creditline(accounts[1], accounts[0], 25)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    gevent.sleep(1)

    assert len(events) == 1
    assert events[0] == (accounts[1], accounts[0], 10)
