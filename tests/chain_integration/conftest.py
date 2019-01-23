import json
import os
import sys

import pytest
from tldeploy.core import deploy_networks, deploy_network

from relay.blockchain.currency_network_proxy import CurrencyNetworkProxy
import eth_tester


NETWORK_SETTINGS = [
        {
            'name': 'Cash',
            'symbol': 'CASH',
            'decimals': 4,
            'fee_divisor': 1000,
            'default_interest_rate': 0,
            'custom_interests': True
        },
        {
            'name': 'Work Hours',
            'symbol': 'HOU',
            'decimals': 4,
            'fee_divisor': 0,
            'default_interest_rate': 1000,
            'custom_interests': False
        },
        {
            'name': 'Beers',
            'symbol': 'BEER',
            'decimals': 0,
            'fee_divisor': 0,
            'custom_interests': False
        }]


"""increate eth_tester's GAS_LIMIT
Otherwise we can't deploy our contract"""
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 6 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 6 * 10 ** 6


@pytest.fixture
def maker(accounts):
    """checksum maker address"""
    return accounts[0]


@pytest.fixture
def maker_key(account_keys):
    """checksum maker address"""
    return account_keys[0].to_bytes()


@pytest.fixture
def taker(accounts):
    """checksum taker address"""
    return accounts[1]


class CurrencyNetworkProxy(CurrencyNetworkProxy):

    def setup_trustlines(self, trustlines):
        for (A, B, clAB, clBA) in trustlines:
            txid = self._proxy.functions.setAccount(A, B, clAB, clBA, 0, 0, 0, 0, 0, 0).transact()
            self._web3.eth.waitForTransactionReceipt(txid)

    def update_trustline(self,
                         from_,
                         to,
                         creditline_given,
                         creditline_received,
                         interest_rate_given=None,
                         interest_rate_received=None):
        if interest_rate_given is None or interest_rate_received is None:
            txid = self._proxy.functions.updateCreditlimits(
                to,
                creditline_given,
                creditline_received).transact({"from": from_})
        else:
            txid = self._proxy.functions.updateTrustline(to,
                                                         creditline_given,
                                                         creditline_received,
                                                         interest_rate_given,
                                                         interest_rate_received).transact({"from": from_})
        self._web3.eth.waitForTransactionReceipt(txid)

    def update_trustline_with_accept(self,
                                     from_,
                                     to,
                                     creditline_given,
                                     creditline_received,
                                     interest_rate_given=None,
                                     interest_rate_received=None):
        self.update_trustline(from_,
                              to,
                              creditline_given,
                              creditline_received,
                              interest_rate_given,
                              interest_rate_received)
        self.update_trustline(to,
                              from_,
                              creditline_received,
                              creditline_given,
                              interest_rate_received,
                              interest_rate_given)

    def transfer(self, from_, to, value, max_fee, path):
        txid = self._proxy.functions.transfer(to, value, max_fee, path).transact({"from": from_})
        self._web3.eth.waitForTransactionReceipt(txid)


@pytest.fixture()
def trustlines(accounts):
    return [(accounts[0], accounts[1], 100, 150),
            (accounts[1], accounts[2], 200, 250),
            (accounts[2], accounts[3], 300, 350),
            (accounts[3], accounts[4], 400, 450),
            (accounts[0], accounts[4], 500, 550)
            ]  # (A, B, clAB, clBA)


def deploy_test_network(web3):
    return deploy_network(web3, 'Trustlines', 'T', 6, fee_divisor=100)


def deploy_test_networks(web3):
    return deploy_networks(web3, NETWORK_SETTINGS)


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


@pytest.fixture()
def testnetwork1_address(web3):
    return deploy_test_network(web3).address


@pytest.fixture()
def testnetwork2_address(web3):
    return deploy_test_network(web3).address


@pytest.fixture()
def testnetwork3_address(web3):
    return deploy_test_network(web3).address


@pytest.fixture()
def testnetworks(web3, maker, taker):
    currency_network_contracts, exchange_contract, unw_eth_contract = deploy_test_networks(web3)

    unw_eth_contract.functions.deposit().transact({'from': taker, 'value': 200})

    currency_network = currency_network_contracts[0]
    currency_network.functions.updateCreditlimits(maker, 300, 0).transact({'from': taker})
    currency_network.functions.updateCreditlimits(taker, 0, 300).transact({'from': maker})

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


@pytest.fixture()
def currency_network(web3, currency_network_abi, testnetwork1_address):
    currency_network = CurrencyNetworkProxy(web3, currency_network_abi, testnetwork1_address)
    return currency_network


@pytest.fixture()
def currency_network_with_trustlines(web3, currency_network_abi, testnetwork2_address, trustlines):
    currency_network = CurrencyNetworkProxy(web3, currency_network_abi, testnetwork2_address)
    currency_network.setup_trustlines(trustlines)

    return currency_network


@pytest.fixture()
def currency_network_with_events(currency_network, accounts):
    currency_network.update_trustline_with_accept(accounts[0], accounts[1], 25, 50)
    currency_network.transfer(accounts[1], accounts[0], 10, 10, [accounts[0]])
    currency_network.update_trustline_with_accept(accounts[0], accounts[2], 25, 50)
    currency_network.update_trustline_with_accept(accounts[0], accounts[4], 25, 50)

    return currency_network


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
