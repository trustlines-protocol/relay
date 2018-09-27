# This file has been copied and adapted from the trustlines-contracts project.
# We like to get rid of the populus dependency and we don't want to compile the
# contracts when running tests in this project.

import os
import sys
import json
from contextlib import contextmanager

from web3 import Web3
from web3.utils.threads import (
    Timeout,
)

contracts = json.load(open(os.path.join(sys.prefix, 'trustlines-contracts', 'build', 'contracts.json')))


class TransactionFailed(Exception):
    pass


def wait_for_transaction_receipt(web3, txid, timeout=180):
    with Timeout(timeout) as time:
            while not web3.eth.getTransactionReceipt(txid):
                time.sleep(5)

    return web3.eth.getTransactionReceipt(txid)


def check_successful_tx(web3: Web3, txid: str, timeout=180) -> dict:
    """See if transaction went through (Solidity code did not throw).
    :return: Transaction receipt
    """
    receipt = wait_for_transaction_receipt(web3, txid, timeout=timeout)
    tx_info = web3.eth.getTransaction(txid)
    status = receipt.get("status", None)
    if receipt["gasUsed"] == tx_info["gas"] or status is False:
        raise TransactionFailed
    return receipt


def wait(transfer_filter):
    with Timeout(30) as timeout:
        while not transfer_filter.get(False):
            timeout.sleep(2)


def get_contract_factory(web3, contract_name):
    contract_interface = contracts[contract_name]
    return web3.eth.contract(
        abi=contract_interface["abi"], bytecode=contract_interface["bytecode"]
    )


def deploy(contract_name, web3, *args):
    contract = get_contract_factory(web3, contract_name)
    txhash = contract.constructor(*args).transact()
    receipt = check_successful_tx(web3, txhash)
    id_address = receipt["contractAddress"]
    return contract(id_address)


# def contract(contract_name, address, chain):
#     return chain.provider.get_contract_factory(contract_name)(address)


def deploy_exchange(web3):
    exchange = deploy("Exchange", web3)
    return exchange


def deploy_unw_eth(web3, exchange_address=None):
    unw_eth = deploy("UnwEth", web3)
    if exchange_address is not None:
        if exchange_address is not None:
            txid = unw_eth.functions.addAuthorizedAddress(exchange_address).transact(
                {"from": web3.eth.accounts[0]})
            check_successful_tx(web3, txid)
    return unw_eth


def deploy_network(web3, name, symbol, decimals, fee_divisor=100, exchange_address=None):
    currency_network = deploy("CurrencyNetwork", web3)

    txid = currency_network.functions.init(name, symbol, decimals, fee_divisor).transact(
        {"from": web3.eth.accounts[0]})
    check_successful_tx(web3, txid)
    if exchange_address is not None:
        txid = currency_network.functions.addAuthorizedAddress(exchange_address).transact(
            {"from": web3.eth.accounts[0]})
        check_successful_tx(web3, txid)

    return currency_network


def deploy_proxied_network(web3, name, symbol, decimals, fee_divisor=100, exchange_address=None):
    currency_network = deploy("CurrencyNetwork", web3)
    currency_network_address = currency_network.address
    print(currency_network_address)
    resolver = deploy("Resolver", web3, currency_network_address)
    proxy = deploy("EtherRouter", web3, resolver.address)
    print(proxy.address)
    proxied_trustlines = get_contract_factory(web3, "CurrencyNetwork")(proxy.address)
    txid = proxied_trustlines.functions.init(name, symbol, decimals, fee_divisor).transact()
    check_successful_tx(web3, txid)
    if exchange_address is not None:
        txid = proxied_trustlines.functions.addAuthorizedAddress(exchange_address).transact()
        check_successful_tx(web3, txid)

    txid = resolver.functions.registerLengthFunction("getUsers()",
                                                     "getUsersReturnSize()",
                                                     currency_network_address).transact()
    check_successful_tx(web3, txid)
    txid = resolver.functions.registerLengthFunction("getFriends(address)",
                                                     "getFriendsReturnSize(address)",
                                                     currency_network_address).transact()
    check_successful_tx(web3, txid)
    txid = resolver.functions.registerLengthFunction("getAccount(address,address)",
                                                     "getAccountLen()",
                                                     currency_network_address).transact()
    check_successful_tx(web3, txid)
    txid = resolver.functions.registerLengthFunction("name()", "nameLen()",
                                                     currency_network_address).transact()
    check_successful_tx(web3, txid)
    txid = resolver.functions.registerLengthFunction("symbol()", "symbolLen()",
                                                     currency_network_address).transact()
    check_successful_tx(web3, txid)
    return proxied_trustlines


@contextmanager
def cd_into_projectpath():
    cwd = os.getcwd()
    install_filepath = os.path.join(sys.prefix, 'trustlines-contracts', 'project.json')

    if os.path.isfile(install_filepath):
        os.chdir(os.path.join(sys.prefix, 'trustlines-contracts'))
        yield
    else:
        raise RuntimeError('Projectfolder not found')
    os.chdir(cwd)


def deploy_networks(web3, networks):
    exchange = deploy_exchange(web3)
    unw_eth = deploy_unw_eth(web3, exchange.address)

    networks = [deploy_network(web3, name, symbol, decimals=decimals, exchange_address=exchange.address) for
                (name, symbol, decimals) in networks]

    return networks, exchange, unw_eth
