import eth_tester
import pytest
from tlbin import load_packaged_contracts
from tldeploy.core import NetworkSettings, deploy_network, deploy_networks
from tldeploy.identity import MetaTransaction

from relay.blockchain import currency_network_proxy

EXPIRATION_TIME = 4102444800  # 01/01/2100


NETWORK_SETTINGS = [
    NetworkSettings(
        name="Cash",
        symbol="CASH",
        fee_divisor=1000,
        custom_interests=True,
        expiration_time=EXPIRATION_TIME,
    ),
    NetworkSettings(
        name="Work Hours",
        symbol="HOU",
        custom_interests=False,
        default_interest_rate=1000,
        expiration_time=EXPIRATION_TIME,
    ),
    NetworkSettings(
        name="Beers", symbol="BEER", decimals=0, expiration_time=EXPIRATION_TIME
    ),
]


"""increate eth_tester's GAS_LIMIT
Otherwise we can't deploy our contract"""
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 6 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6


@pytest.fixture()
def expiration_time():
    return EXPIRATION_TIME


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


class CurrencyNetworkProxy(currency_network_proxy.CurrencyNetworkProxy):
    def setup_trustlines(self, trustlines):
        for (A, B, clAB, clBA, intAB, intBA, is_frozen, balanceAB) in trustlines:
            self.update_trustline_with_accept(
                A, B, clAB, clBA, intAB, intBA, is_frozen, balanceAB
            )

    def update_trustline(
        self,
        from_,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given=None,
        interest_rate_received=None,
        is_frozen=False,
        transfer=0,
    ):
        txid = self.update_trustline_function_call(
            to,
            creditline_given,
            creditline_received,
            interest_rate_given,
            interest_rate_received,
            is_frozen,
            transfer,
        ).transact({"from": from_})

        self._web3.eth.waitForTransactionReceipt(txid)
        return txid

    def update_trustline_function_call(
        self,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given=None,
        interest_rate_received=None,
        is_frozen=False,
        transfer=0,
    ):

        if interest_rate_given is None or interest_rate_received is None:
            return self._proxy.functions.updateCreditlimits(
                to, creditline_given, creditline_received
            )
        elif transfer == 0:
            return self._proxy.functions.updateTrustline(
                to,
                creditline_given,
                creditline_received,
                interest_rate_given,
                interest_rate_received,
                is_frozen,
            )
        else:
            return self._proxy.functions.updateTrustline(
                to,
                creditline_given,
                creditline_received,
                interest_rate_given,
                interest_rate_received,
                is_frozen,
                transfer,
            )

    def cancel_trustline_update(self, from_, to):
        txid = self._proxy.functions.cancelTrustlineUpdate(to).transact({"from": from_})
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
        transfer=0,
    ):
        self.update_trustline(
            from_,
            to,
            creditline_given,
            creditline_received,
            interest_rate_given,
            interest_rate_received,
            is_frozen,
            transfer,
        )
        return self.update_trustline(
            to,
            from_,
            creditline_received,
            creditline_given,
            interest_rate_received,
            interest_rate_given,
            is_frozen,
            -transfer,
        )

    def update_trustline_and_cancel(
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
        self.cancel_trustline_update(from_, to)

    def update_trustline_and_reject(
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
        self.cancel_trustline_update(to, from_)

    def close_trustline(self, from_, to):
        self._proxy.functions.closeTrustline(to).transact({"from": from_})

    def settle_and_close_trustline(self, from_, to):
        balance = self.get_balance(from_, to)
        if balance > 0:
            self.transfer(from_, balance, max_fee=0, path=[from_, to])
        elif balance < 0:
            self.transfer(to, -balance, max_fee=0, path=[to, from_])

        self.close_trustline(from_, to)

    def transfer(self, from_, value, max_fee, path, extra_data=b""):
        tx_id = self._proxy.functions.transfer(
            value, max_fee, path, extra_data
        ).transact({"from": from_})
        self._web3.eth.waitForTransactionReceipt(tx_id)

    def transfer_on_path(self, value, path, max_fee=None, extra_data=b""):
        if max_fee is None:
            max_fee = value
        tx_id = self._proxy.functions.transfer(
            value, max_fee, path, extra_data
        ).transact({"from": path[0]})
        self._web3.eth.waitForTransactionReceipt(tx_id)
        return tx_id

    def transfer_receiver_pays_on_path(self, value, path, max_fee=None, extra_data=b""):
        if max_fee is None:
            max_fee = value
        tx_id = self._proxy.functions.transferReceiverPays(
            value, max_fee, path, extra_data
        ).transact({"from": path[0]})
        self._web3.eth.waitForTransactionReceipt(tx_id)
        return tx_id

    def transfer_meta_transaction(self, value, max_fee, path, extra_data=b""):

        function_call = self._proxy.functions.transfer(value, max_fee, path, extra_data)
        meta_transaction = MetaTransaction.from_function_call(
            function_call, to=self.address
        )

        return meta_transaction

    def trustline_update_meta_transaction(
        self,
        to,
        creditline_given,
        creditline_received,
        interest_rate_given,
        interest_rate_received,
        is_frozen,
        transfer,
    ):

        function_call = self.update_trustline_function_call(
            to,
            creditline_given,
            creditline_received,
            interest_rate_given,
            interest_rate_received,
            is_frozen,
            transfer,
        )
        meta_transaction = MetaTransaction.from_function_call(
            function_call, to=self.address
        )

        return meta_transaction

    def get_balance(self, from_, to):
        return self._proxy.functions.balance(from_, to).call()

    def freeze_network(self):
        return self._proxy.functions.testFreezeNetwork().transact()

    def time_travel_to_expiration(self, chain):
        expiration_time = self._proxy.functions.expirationTime().call()
        chain.time_travel(expiration_time)
        chain.mine_block()

    def unfreeze_network(self):
        return self._proxy.functions.testUnfreezeNetwork().transact()

    def increase_debt(self, debtor, creditor, value):
        tx_id = self._proxy.functions.increaseDebt(creditor, value).transact(
            {"from": debtor}
        )
        self._web3.eth.waitForTransactionReceipt(tx_id)
        return tx_id

    def get_debt(self, debtor, creditor):
        return self._proxy.functions.getDebt(debtor, creditor).call()

    def assert_debt_value(self, debtor, creditor, value):
        assert self.get_debt(debtor, creditor) == value


@pytest.fixture(scope="session")
def trustlines(accounts):
    return [
        (accounts[0], accounts[1], 100, 150, 0, 0, False, 0),
        (accounts[1], accounts[2], 200, 250, 0, 0, False, 0),
        (accounts[2], accounts[3], 300, 350, 0, 0, False, 0),
        (accounts[3], accounts[4], 400, 450, 0, 0, False, 0),
        (accounts[4], accounts[5], 400, 450, 0, 0, False, 0),
        (accounts[5], accounts[6], 400, 450, 0, 0, False, 0),
        (accounts[0], accounts[4], 500, 550, 0, 0, False, 0),
    ]  # (A, B, clAB, clBA, intAB, intBA, frozen, transferAB)


@pytest.fixture(scope="session")
def trustlines_with_interests(accounts):
    return [
        (accounts[0], accounts[1], 12345, 12345, 2000, 1000, False, 0),
        (accounts[1], accounts[2], 12345, 12345, 2000, 1000, False, 0),
        (accounts[2], accounts[3], 12345, 12345, 2000, 1000, False, 0),
        (accounts[3], accounts[4], 12345, 12345, 2000, 1000, False, 0),
        (accounts[0], accounts[4], 12345, 12345, 2000, 1000, False, 0),
    ]  # (A, B, clAB, clBA, intAB, intBA, frozen, transferAB)


def deploy_currency_network_v2(web3):
    return deploy_network(
        web3,
        network_settings=NetworkSettings(
            fee_divisor=100,
            name="Trustlines",
            symbol="T",
            custom_interests=True,
            expiration_time=EXPIRATION_TIME,
        ),
        currency_network_contract_name="CurrencyNetworkV2",
    )


def deploy_test_networks(web3):
    return deploy_networks(web3, NETWORK_SETTINGS)


@pytest.fixture(scope="session")
def contracts():
    return load_packaged_contracts()


@pytest.fixture(scope="session")
def currency_network_v2_abi(contracts):
    return contracts["CurrencyNetworkV2"]["abi"]


@pytest.fixture(scope="session")
def exchange_abi(contracts):
    return contracts["Exchange"]["abi"]


@pytest.fixture(scope="session")
def token_abi(contracts):
    return contracts["Token"]["abi"]


@pytest.fixture(scope="session")
def testnetwork1_address(web3):
    return deploy_currency_network_v2(web3).address


@pytest.fixture(scope="session")
def testnetwork2_address(web3):
    return deploy_currency_network_v2(web3).address


@pytest.fixture(scope="session")
def testnetwork3_address(web3, chain):
    return deploy_currency_network_v2(web3).address


@pytest.fixture(scope="session")
def testnetwork4_address(web3):
    return deploy_currency_network_v2(web3).address


@pytest.fixture()
def testnetworks(web3, maker, taker):
    (
        currency_network_contracts,
        exchange_contract,
        unw_eth_contract,
    ) = deploy_test_networks(web3)

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


@pytest.fixture(scope="session")
def currency_network(web3, currency_network_v2_abi, testnetwork1_address):
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_v2_abi, testnetwork1_address
    )
    return currency_network


@pytest.fixture()
def currency_network_with_trustlines(
    web3, currency_network_v2_abi, testnetwork2_address, trustlines
):
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_v2_abi, testnetwork2_address
    )
    currency_network.setup_trustlines(trustlines)

    return currency_network


@pytest.fixture()
def currency_network_with_trustlines_and_interests(
    web3, currency_network_v2_abi, testnetwork2_address, trustlines_with_interests
):
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_v2_abi, testnetwork2_address
    )
    currency_network.setup_trustlines(trustlines_with_interests)

    return currency_network


@pytest.fixture(scope="session")
def currency_network_with_trustlines_and_interests_session(
    web3, currency_network_v2_abi, testnetwork3_address, trustlines_with_interests
):
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_v2_abi, testnetwork3_address
    )
    currency_network.setup_trustlines(trustlines_with_interests)

    return currency_network


@pytest.fixture(scope="session")
def currency_network_with_trustlines_session(
    web3, currency_network_v2_abi, testnetwork4_address, trustlines
):
    currency_network = CurrencyNetworkProxy(
        web3, currency_network_v2_abi, testnetwork4_address
    )
    currency_network.setup_trustlines(trustlines)

    return currency_network


@pytest.fixture(scope="session")
def test_currency_network_v1(
    web3, currency_network_v2_abi, testnetwork1_address, contracts
):
    """This is the only remaining contract of type `TestCurrencyNetwork`.
    It should only be used for its test functions of unfreezing a network"""
    network = deploy_network(
        web3,
        network_settings=NetworkSettings(
            fee_divisor=100,
            name="Trustlines",
            symbol="T",
            custom_interests=True,
            expiration_time=EXPIRATION_TIME,
        ),
        currency_network_contract_name="TestCurrencyNetwork",
    )
    return CurrencyNetworkProxy(
        web3, contracts["TestCurrencyNetwork"]["abi"], network.address
    )


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
