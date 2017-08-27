import os
import json
import codecs
import socket
import logging
from contextlib import contextmanager

import gevent
from web3 import Web3, RPCProvider
from solc import compile_files
from ethereum import abi, transactions

from tlgraph import Friendship
from logger import getLogger
from utils import add_0x_prefix


logger = getLogger('tl_helper', logging.DEBUG)


# Constants
REGISTRY = 'Registry'
TRUSTLINE = 'Trustlines'
TrustlineUpdatedEvent = 'CreditlineUpdate'
BalanceUpdatedEvent = 'BalanceUpdate'
TransferEvent = 'Transfer'

queryBlock = 'pending'
updateBlock = 'pending'

sync_interval = 300 # 5min
reconnect_interval = 3 # 3s

def write_config_json(key, value):
    with codecs.open("config.json", 'r', 'utf8') as data_file:
        data = json.load(data_file)
    data[key] = value
    with codecs.open('config.json', 'w', 'utf8') as f:
        json.dump(data, f)


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


class Trustline(object):

    fileDir = os.path.dirname(os.path.realpath('__file__'))

    def __init__(self):
        self.config = self.read_config()
        self.host = self.config.get('rpc').get('host')
        self.port = self.config.get('rpc').get('port')
        self.ssl = self.config.get('rpc').get('ssl')
        self.web3 = Web3(RPCProvider(self.host, self.port, ssl=self.ssl))
        self.web3.eth.defaultBlock = queryBlock
        # self.registry_address = self.config.get('registry')
        # self.registry_proxy = None
        # self.registry_abi = None
        self.tl_proxies = {}
        self.trustline_abi = None
        self.trustline_code = None

    def read_config(self):
        with open('config.json') as data_file:
            return json.load(data_file)

    def initialise_app(self):
            # self.initialise_registry_contract()
            self.initialise_trustline_abi()
            self.initialise_proxies()

    def initialise_proxies(self):
        for token_address in self.get_token_list():
            self.tl_proxies[token_address] = self.web3.eth.contract(abi=self.trustline_abi, address=token_address)

    def initialise_trustline_abi(self):
        with cd(os.path.join(self.fileDir, '../contracts/')):
            compiled_contract = compile_files(['it_set_lib.sol', 'trustlines.sol'])
            self.trustline_abi = compiled_contract.get('trustlines.sol:Trustlines').get('abi')
            self.trustline_code = compiled_contract.get('trustlines.sol:Trustlines').get('bin')

    def initialise_registry_contract(self):
        with cd(os.path.join(self.fileDir, '../contracts/')):
            compiled_contracts = compile_files(['NameAddressLibrary.sol', 'registry.sol'])
            self.registry_proxy = self.web3.eth.contract(
                abi=compiled_contracts.get('Registry').get('abi'),
                address=self.registry_address)
            self.registry_abi = compiled_contracts.get('Registry').get('abi')

    def start_listen_on_balance(self, address, function):
        def log(log_entry):
            function(log_entry['args']['_from'], log_entry['args']['_to'], log_entry['args']['_value'])
        self.start_listen_on(address, BalanceUpdatedEvent, log)

    def start_listen_on_trustline(self, address, function):
        def log(log_entry):
            function(log_entry['args']['_creditor'], log_entry['args']['_debtor'], log_entry['args']['_value'])
        self.start_listen_on(address, TrustlineUpdatedEvent, log)

    def start_listen_on_transfer(self, address):
        def log(log_entry):
            pass
        self.start_listen_on(address, TransferEvent, log, {'fromBlock': 'pending', 'toBlock': 'pending' })

    def watch_filter(self, address, eventname, function, params=None):
        while True:
            try:
                filter = self.tl_proxies[address].on(eventname, params)
                filter.watch(function)
                logger.info('Connected to filter for {}'.format(eventname))
                return filter
            except socket.timeout as err:
                logger.warning('Timeout in filter creation, try to reconnect: ' + str(err))
                gevent.sleep(reconnect_interval)
            except socket.error as err:
                logger.warning('Socketerror in filter creation, try to reconnect:' + str(err))
                gevent.sleep(reconnect_interval)
            except ValueError as err:
                logger.warning('ValueError in filter creation, try to reconnect:' + str(err))
                gevent.sleep(reconnect_interval)

    def start_listen_on(self, address, eventname, function, params=None):
        def on_exception(filter):
            logger.warning('Filter {} disconnected, trying to reconnect'.format(filter.filter_id))
            filter = self.watch_filter(address, eventname, function, params)
            filter.link_exception(on_exception)
        if params is None:
            params = {}
        params.setdefault('fromBlock', updateBlock)
        params.setdefault('toBlock', updateBlock)
        filter = self.watch_filter(address, eventname, function, params)
        filter.link_exception(on_exception)

    def start_listen_on_full_sync(self, address, function):
        def sync():
            while True:
                try:
                    function(self.get_graph_representation(address))
                    gevent.sleep(sync_interval)
                except socket.timeout as err:
                    logger.warning('Full sync failed because of timeout, try again: ' + str(err))
                    gevent.sleep(reconnect_interval)
                except socket.error as err:
                    logger.warning('Full sync failed because of error, try again: ' + str(err))
                    gevent.sleep(reconnect_interval)

        gevent.Greenlet.spawn(sync)

    def create_token(self, name, symbol, decimal):
        constructor_args = [name, symbol, decimal]
        tltoken_transaction_hash = self.web3.eth.contract(abi=self.trustline_abi, bytecode=self.trustline_code).deploy(args=constructor_args)
        tltoken_transaction_receipt = self.web3.eth.getTransactionReceipt(tltoken_transaction_hash)
        tltoken_address = tltoken_transaction_receipt.get('contractAddress')
        # self.registry_proxy.transact({'from': self.web3.eth.coinbase}).register(name, tltoken_address)
        # self.tltoken_dict[tltoken_address] = self.web3.eth.contract(self.trustline_abi, address=tltoken_address)
        # TODO start listen on event from contract
        return tltoken_address

    def get_token_list(self):
        return os.environ.get('TL_TOKEN_LIST', '').split()

    def get_name(self, token_address):
        return self.tl_proxies[token_address].call().name().strip("\0")

    def get_address(self, token_name):
        return next((token_address for token_address in self.get_token_list() if self.get_name(token_address) == token_name), None)

    def get_friends(self, token_address, user_address):
        return [addr for addr in self.tl_proxies[token_address].call().friends(user_address)]

    def get_account(self, token_address, a_address, b_address):
        return self.tl_proxies[token_address].call().trustline(a_address, b_address)

    def get_token_info(self, token_address):
        logger.debug('Get token info')
        tltoken_proxy = self.tl_proxies[token_address]
        return {'name': tltoken_proxy.call().name(),
                'symbol': tltoken_proxy.call().symbol(),
                'decimals': tltoken_proxy.call().decimals(),
                'numUsers': len(tltoken_proxy.call().users()),
                'transfers': self.get_number_of_transfers(token_address),
                'transferred': self.get_total_transferred(token_address)}

    def get_users(self, token_address):
        return [addr for addr in self.tl_proxies[token_address].call().users()]

    def get_token_address(self, token_name):
        return self.registry_proxy.call().getTLTokenAddress(token_name)

    def get_tx_infos(self, user_address):
        return {'balance': self.web3.eth.getBalance(user_address),
                'nonce': self.web3.eth.getTransactionCount(user_address),
                'gasPrice': self.web3.eth.gasPrice}

    def get_graph_representation(self, token_address):
        """Returns the trustlines network as a dict address -> list of Friendships"""
        result = {}
        for user in self.get_users(token_address):
            list = []
            for friend in self.get_friends(token_address, user):
                if user < friend:
                    trustline_ab, trustline_ba, balance_ab = self.get_account(token_address, user, friend)
                    list.append(Friendship(friend, trustline_ab, trustline_ba, balance_ab))
            result[user] = list
        return result

    # <- for testing sender key has to be unlocked
    def update_trustline(self, token_address, sender, receiver, value):
        self.tl_proxies[token_address].transact({'from': sender}).updateCreditline(receiver, value)

    def mediated_transfer(self, token_address, sender, receiver, value, path):
        self.tl_proxies[token_address].transact({'from': sender}).mediatedTransfer(receiver, value, path)
    # -> for testing

    def new_user(self, user_address):
        if self.web3.eth.getBalance(user_address) == 0:
            return self.web3.eth.sendTransaction({
                'from': self.web3.eth.coinbase,
                'to': user_address,
                'value': 1000000000000000000
            })
        else:
            return False

    def get_token_abi(self):
        return self.trustline_abi

    def relay_tx(self, rawtxn):
        return self.web3.eth.sendRawTransaction(rawtxn)

    def getTransactionReceipt(self, txn_hash):
        self.web3.eth.getTransactionReceipt(txn_hash)

    def prepare_txn(self, token_address, sender, function_name, arguments):
        ct = abi.ContractTranslator(self.trustline_abi)
        if isinstance(arguments, list):
            cdata = ct.encode_function_call(function_name, args=arguments)
        return transactions.Transaction(nonce=self.web3.eth.getTransactionCount(sender),
                                        gasprice=self.web3.eth.gasPrice,
                                        startgas=100000,
                                        to=token_address,
                                        value=0,
                                        data=cdata)

    def get_events(self, token_address, event_name, from_block):
        if from_block > self.get_block():
            return []
        filter = self.tl_proxies[token_address].pastEvents(event_name, {'fromBlock': from_block, 'toBlock': queryBlock})
        return filter.get(only_changes=False)

    def list_transfers(self, token_address, user_address, from_block):
        return [merge_two_dicts(event.get('args'), {'blockNumber': event.get('blockNumber'), 'event': event.get('event'), 'transactionHash': event.get('transactionHash')})
                for event in self.get_events(token_address, TransferEvent, from_block) if ((event.get('args').get('_from')) == user_address or
                         (event.get('args').get('_to')) == user_address)]

    def poll_events(self, token_address, user_address, from_block):
        return sorted([merge_two_dicts(event.get('args'), {'blockNumber': event.get('blockNumber'), 'event': event.get('event'), 'transactionHash': event.get('transactionHash')})
                for event in self.get_events(token_address, TrustlineUpdatedEvent, from_block)
                    if event.get('args').get('_creditor') == user_address or
                         event.get('args').get('_debtor') == user_address] +
                            self.list_transfers(token_address, user_address, from_block), key=lambda x: x.get('blockNumber', 0))

    def get_block(self):
        return self.web3.eth.blockNumber

    def get_token_names(self):
        return [name.strip("\0") for name in self.registry_proxy.call().getAllNames()]

    def get_total_transferred(self, token_address):
        return sum([event.get('args').get('_value') for event in self.get_events(token_address, TransferEvent, 1)])

    def get_number_of_transfers(self, token_address):
        return len(self.get_events(token_address, TransferEvent, 1))



if __name__ == '__main__':
    trustline = Trustline()
    trustline.initialise_app()
    #print trustline.web3.eth.accounts[0]
    #print trustline.get_token_address('Shopcoin')
    #print trustline.poll_events(trustline.get_token_address('Shopcoin'), trustline.web3.eth.accounts[0], 1)
    #print trustline.poll_events(trustline.get_token_address('Shopcoin'), trustline.web3.eth.accounts[0], 29)
