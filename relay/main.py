import json
import logging
import os
import sys

import gevent
from eth_utils import is_checksum_address, to_checksum_address
from gevent import sleep
from gevent.wsgi import WSGIServer
from sqlalchemy import create_engine
from web3 import Web3, RPCProvider

from .blockchain.exchange_proxy import ExchangeProxy
from .blockchain.currency_network_proxy import CurrencyNetworkProxy
from .blockchain.node import Node
from .network_graph.graph import CurrencyNetworkGraph
from .api.app import ApiApp
from .exchange.orderbook import OrderBookGreenlet
from .logger import get_logger

logger = get_logger('trustlines', logging.DEBUG)


class TrustlinesRelay:

    def __init__(self):
        self.currency_network_proxies = {}
        self.currency_network_graphs = {}
        self.config = {}
        self.contracts = {}
        self.node = None
        self._web3 = None
        self.orderbook = None
        self.unw_eth = None

    @property
    def networks(self):
        return self.currency_network_proxies.keys()

    @property
    def exchanges(self):
        return self.orderbook.exchange_addresses

    def is_currency_network(self, address: str) -> bool:
        return address in self.networks

    def is_trusted_token(self, address: str) -> bool:
        return address == self.unw_eth

    def start(self):
        logger.info('Starting relay server')
        self._load_config()
        self._load_contracts()
        self._load_orderbook()
        self._web3 = Web3(
            RPCProvider(
                self.config['rpc']['host'],
                self.config['rpc']['port'],
                ssl=self.config['rpc']['ssl']
            )
        )
        self.node = Node(self._web3)
        self._start_listen_on_new_addresses()
        ipport = ('', 5000)
        app = ApiApp(self)
        http_server = WSGIServer(ipport, app, log=None)
        logger.info('Server is running on {}'.format(ipport))
        http_server.serve_forever()

    def new_network(self, address):
        assert is_checksum_address(address)
        if address in self.networks:
            return
        logger.info('New network: {}'.format(address))
        self.currency_network_graphs[address] = CurrencyNetworkGraph(100)
        self.currency_network_proxies[address] = CurrencyNetworkProxy(self._web3,
                                                                      self.contracts['CurrencyNetwork']['abi'],
                                                                      address)
        self._start_listen_network(address)

    def new_exchange(self, address):
        assert is_checksum_address(address)
        if address not in self.exchanges:
            logger.info('New Exchange contract: {}'.format(address))
            self.orderbook.add_exchange(ExchangeProxy(self._web3,
                                                      self.contracts['Exchange']['abi'],
                                                      self.contracts['Token']['abi'],
                                                      address,
                                                      self))

    def new_unw_eth(self, address):
        assert is_checksum_address(address)
        if self.unw_eth != address:
            logger.info('New Unwrap ETH contract: {}'.format(address))
            self.unw_eth = address

    def get_networks_of_user(self, user_address):
        assert is_checksum_address(user_address)
        networks_of_user = []
        for network_address in self.networks:
            if user_address in self.currency_network_graphs[network_address].users:
                networks_of_user.append(network_address)
        return networks_of_user

    def _load_config(self):
        with open('config.json') as data_file:
            self.config = json.load(data_file)

    def _load_contracts(self):
        with open(os.path.join(sys.prefix, 'trustlines-contracts', 'build', 'contracts.json')) as data_file:
            self.contracts = json.load(data_file)

    def _load_orderbook(self):
        self.orderbook = OrderBookGreenlet()
        self.orderbook.connect_db(create_engine('sqlite:///:memory:'))
        self.orderbook.start()

    def _load_addresses(self):
        with open('addresses.json') as data_file:
            try:
                addresses = json.load(data_file)
                for address in addresses['networks']:
                    self.new_network(to_checksum_address(address))
                self.new_exchange(to_checksum_address(addresses['exchange']))
                self.new_unw_eth(to_checksum_address(addresses['unwEth']))
            except json.decoder.JSONDecodeError as e:
                logger.error('Could not read addresses.json:' + str(e))

    def _start_listen_network(self, address):
        assert is_checksum_address(address)
        graph = self.currency_network_graphs[address]
        proxy = self.currency_network_proxies[address]
        link_graph(proxy, graph, full_sync_interval=self.config.get('syncInterval', 300))

    def _start_listen_on_new_addresses(self):
        def listen():
            while True:
                self._load_addresses()
                sleep(self.config.get('updateNetworksInterval', 120))

        gevent.Greenlet.spawn(listen)


def link_graph(proxy, graph, full_sync_interval=None):
    if full_sync_interval is not None:
        proxy.start_listen_on_full_sync(_create_on_full_sync(graph), full_sync_interval)
    proxy.start_listen_on_balance(_create_on_balance(graph))
    proxy.start_listen_on_creditline(_create_on_creditline(graph))
    proxy.start_listen_on_trustline(_create_on_trustline(graph))


def _create_on_balance(graph):
    def update_balance(a, b, balance):
        graph.update_balance(a, b, balance)

    return update_balance


def _create_on_creditline(graph):
    def update_creditline(a, b, creditline):
        graph.update_creditline(a, b, creditline)

    return update_creditline


def _create_on_trustline(graph):
    def update_trustline(a, b, creditline_given, creditline_received):
        graph.update_trustline(a, b, creditline_given, creditline_received)

    return update_trustline


def _create_on_full_sync(graph):
    def update_community(graph_rep):
        graph.gen_network(graph_rep)

    return update_community


def main():
    trustlines = TrustlinesRelay()
    trustlines.start()


if __name__ == '__main__':
    main()
