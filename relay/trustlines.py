import json
import logging
import os
import sys

import gevent
from gevent import sleep
from gevent.wsgi import WSGIServer
from web3 import Web3, RPCProvider
from eth_utils import to_checksum_address, is_checksum_address

from relay.api.app import ApiApp
from relay.currency_network import CurrencyNetwork
from relay.graph import CurrencyNetworkGraph
from relay.logger import get_logger
from relay.node import Node

logger = get_logger('trustlines', logging.DEBUG)


class Trustlines:

    def __init__(self):
        self.currency_network_proxies = {}
        self.currency_network_graphs = {}
        self.config = {}
        self.contracts = {}
        self.node = None
        self._web3 = None

    @property
    def networks(self):
        return self.currency_network_proxies.keys()

    def start(self):
        logger.info('Starting relay server')
        self.load_config()
        self.load_contracts()
        self._web3 = Web3(
            RPCProvider(
                self.config['rpc']['host'],
                self.config['rpc']['port'],
                ssl=self.config['rpc']['ssl']
            )
        )
        self.node = Node(self._web3)
        self._start_listen_on_new_networks()
        ipport = ('', 5000)
        app = ApiApp(self)
        http_server = WSGIServer(ipport, app, log=None)
        logger.info('Server is running on {}'.format(ipport))
        http_server.serve_forever()

    def load_config(self):
        with open('config.json') as data_file:
            self.config = json.load(data_file)

    def load_contracts(self):
        with open(os.path.join(sys.prefix, 'trustlines-contracts', 'build', 'contracts.json')) as data_file:
            self.contracts = json.load(data_file)

    def new_network(self, address):
        assert is_checksum_address(address)
        if address in self.networks:
            return
        logger.info('New network: {}'.format(address))
        self.currency_network_graphs[address] = CurrencyNetworkGraph()
        self.currency_network_proxies[address] = CurrencyNetwork(self._web3,
                                                                 self.contracts['CurrencyNetwork']['abi'],
                                                                 address)
        self._start_listen_network(address)

    def load_networks(self):
        with open('networks') as f:
            networks = f.read().splitlines()
        for address in networks:
            self.new_network(to_checksum_address(address))

    def get_networks_of_user(self, user_address):
        assert is_checksum_address(user_address)
        networks_of_user = []
        for network_address in self.networks:
            if user_address in self.currency_network_graphs[network_address].users:
                networks_of_user.append(network_address)
        return networks_of_user

    def _start_listen_network(self, address):
        assert is_checksum_address(address)
        graph = self.currency_network_graphs[address]
        proxy = self.currency_network_proxies[address]
        proxy.start_listen_on_full_sync(_create_on_full_sync(graph), self.config.get('syncInterval', 300))
        proxy.start_listen_on_balance(_create_on_balance(graph))
        proxy.start_listen_on_creditline(_create_on_trustline(graph))

    def _start_listen_on_new_networks(self):
        def listen():
            while True:
                self.load_networks()
                sleep(self.config.get('updateNetworksInterval', 120))

        gevent.Greenlet.spawn(listen)


def _create_on_balance(graph):
    def update_balance(a, b, balance):
        graph.update_balance(a, b, balance)

    return update_balance


def _create_on_trustline(graph):
    def update_balance(a, b, balance):
        graph.update_creditline(a, b, balance)

    return update_balance


def _create_on_full_sync(graph):
    def update_community(graph_rep):
        graph.gen_network(graph_rep)

    return update_community


def main():
    trustlines = Trustlines()
    trustlines.start()


if __name__ == '__main__':
    main()
