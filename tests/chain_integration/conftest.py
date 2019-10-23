import json
import os
import sys

import eth_tester
import pytest
from tldeploy.core import deploy_network, deploy_networks
from tldeploy.identity import MetaTransaction

from relay.blockchain.currency_network_proxy import CurrencyNetworkProxy

EXPIRATION_TIME = 4102444800  # 01/01/2100


NETWORK_SETTINGS = [
    {
        "name": "Cash",
        "symbol": "CASH",
        "decimals": 4,
        "fee_divisor": 1000,
        "default_interest_rate": 0,
        "custom_interests": True,
        "account_management_enabled": True,
        "expiration_time": EXPIRATION_TIME,
    },
    {
        "name": "Work Hours",
        "symbol": "HOU",
        "decimals": 4,
        "fee_divisor": 0,
        "default_interest_rate": 1000,
        "custom_interests": False,
        "account_management_enabled": True,
        "expiration_time": EXPIRATION_TIME,
    },
    {
        "name": "Beers",
        "symbol": "BEER",
        "decimals": 0,
        "fee_divisor": 0,
        "custom_interests": False,
        "account_management_enabled": True,
        "expiration_time": EXPIRATION_TIME,
    },
]


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
            txid = self._proxy.functions.setAccount(
                A, B, clAB, clBA, 0, 0, False, 0, 0, 0, 0
            ).transact()
            self._web3.eth.waitForTransactionReceipt(txid)

    def update_trustline(
        self,
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given=None,
        interest_rate_received=None,
        is_frozen=False,
    ):
        if interest_rate_given is None or interest_rate_received is None:
            txid = self._proxy.functions.updateCreditlimits(
                to, creditline_given, creditline_received
            ).transact({"from": from_})
        else:
            txid = self._proxy.functions.updateTrustline(
                to,
                creditline_given,
                creditline_received,
                interest_rate_given,
                interest_rate_received,
                is_frozen,
            ).transact({"from": from_})
        self._web3.eth.waitForTransactionReceipt(txid)

    def update_trustline_with_accept(
        self,
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given=None,
        interest_rate_received=None,
        is_frozen=False,
    ):
        self.update_trustline(
            from_,
            to,
            creditline_given,
            creditline_received,
            interest_rate_given,
            interest_rate_received,
            is_frozen,
        )
        self.update_trustline(
            to,
            from_,
            creditline_received,
            creditline_given,
            interest_rate_received,
            interest_rate_given,
            is_frozen,
        )

    def transfer(self, from_, to, value, max_fee, path, extra_data=b""):
        txid = self._proxy.functions.transfer(
            to, value, max_fee, path, extra_data
        ).transact({"from": from_})
        self._web3.eth.waitForTransactionReceipt(txid)

    def transfer_meta_transaction(self, to, value, max_fee, path, extra_data=b""):

        function_call = self._proxy.functions.transfer(
            to, value, max_fee, path, extra_data
        )
        meta_transaction = MetaTransaction.from_function_call(
            function_call, to=self.address
        )

        return meta_transaction

    def get_balance(self, from_, to):
        return self._proxy.functions.balance(from_, to).call()


@pytest.fixture()
def trustlines(accounts):
    return [
        (accounts[0], accounts[1], 100, 150),
        (accounts[1], accounts[2], 200, 250),
        (accounts[2], accounts[3], 300, 350),
        (accounts[3], accounts[4], 400, 450),
        (accounts[0], accounts[4], 500, 550),
    ]  # (A, B, clAB, clBA)


def deploy_test_network(web3):
    return deploy_network(
        web3,
        "Trustlines",
        "T",
        6,
        fee_divisor=100,
        account_management_enabled=True,
        expiration_time=EXPIRATION_TIME,
    )


def deploy_test_networks(web3):
    return deploy_networks(web3, NETWORK_SETTINGS)


@pytest.fixture(scope="session")
def contracts():
    with open(
        os.path.join(sys.prefix, "trustlines-contracts", "build", "contracts.json")
    ) as data_file:
        return json.load(data_file)


@pytest.fixture(scope="session")
def currency_network_abi(contracts):
    return contracts["CurrencyNetwork"]["abi"]


@pytest.fixture(scope="session")
def exchange_abi(contracts):
    return contracts["Exchange"]["abi"]


@pytest.fixture(scope="session")
def token_abi(contracts):
    return contracts["Token"]["abi"]


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
    currency_network_contracts, exchange_contract, unw_eth_contract = deploy_test_networks(
        web3
    )

    unw_eth_contract.functions.deposit().transact({"from": taker, "value": 200})

    currency_network = currency_network_contracts[0]
    currency_network.functions.updateCreditlimits(maker, 300, 0).transact(
        {"from": taker}
    )
    currency_network.functions.updateCreditlimits(taker, 0, 300).transact(
        {"from": maker}
    )

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
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_abi, testnetwork1_address
    )
    return currency_network


@pytest.fixture()
def currency_network_with_trustlines(
    web3, currency_network_abi, testnetwork2_address, trustlines
):
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_abi, testnetwork2_address
    )
    currency_network.setup_trustlines(trustlines)

    return currency_network


@pytest.fixture()
def currency_network_with_events(currency_network, accounts, test_extra_data):
    currency_network.update_trustline_with_accept(accounts[0], accounts[1], 25, 50)
    currency_network.transfer(
        accounts[1], accounts[0], 10, 10, [accounts[0]], test_extra_data
    )
    currency_network.update_trustline_with_accept(accounts[0], accounts[2], 25, 50)
    currency_network.update_trustline_with_accept(accounts[0], accounts[4], 25, 50)

    return currency_network


@pytest.fixture()
def address_oracle(testnetworks):
    class AddressOracle:
        def is_currency_network(self, address):
            return address in [network.address for network in testnetworks[0]]

        def is_trusted_token(self, address):
            print(address)
            print(testnetworks[2].address)
            return address == testnetworks[2].address

    return AddressOracle()
