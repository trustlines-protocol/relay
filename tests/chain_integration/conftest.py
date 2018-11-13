import json
import os
import sys

import pytest
from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider
from eth_utils import to_checksum_address, encode_hex
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


@pytest.fixture(scope="session", autouse=True)
def increase_gas_limit():
    """increate eth_tester's GAS_LIMIT
    Otherwise we can't deploy our contract"""
    assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 6 * 10 ** 6
    eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 6 * 10 ** 6


@pytest.fixture(scope="session")
def ethereum_tester_session(test_account):
    """Returns an instance of an Ethereum tester"""
    tester = eth_tester.EthereumTester(eth_tester.PyEVMBackend())
    a0 = tester.add_account(encode_hex(test_account.private_key))
    faucet = tester.get_accounts()[0]
    tester.send_transaction(
        {"from": faucet,
         "to": to_checksum_address(a0),
         "gas": 21000,
         "value": 10000000})
    return tester


@pytest.fixture
def ethereum_tester(ethereum_tester_session):
    tester = ethereum_tester_session
    snapshot = tester.take_snapshot()
    yield tester
    tester.revert_to_snapshot(snapshot)


@pytest.fixture()
def web3(ethereum_tester):
    web3 = Web3(EthereumTesterProvider(ethereum_tester))
    web3.eth.defaultAccount = web3.eth.accounts[0]
    return web3

    # return Web3(HTTPProvider('http://127.0.0.1:8545'))


@pytest.fixture()
def accounts(web3):
    accounts = web3.personal.listAccounts[0:5]
    assert len(accounts) == 5
    return [to_checksum_address(account) for account in accounts]


@pytest.fixture
def maker(test_account):
    """checksum maker address"""
    return test_account.address


@pytest.fixture
def taker(web3):
    """checksum taker address"""
    return to_checksum_address(web3.personal.listAccounts[0])


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
            txid = self._proxy.functions.updateTrustline(to,
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
    currency_network.functions.updateTrustline(maker, 300, 0).transact({'from': taker})
    currency_network.functions.updateTrustline(taker, 0, 300).transact({'from': maker})

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
