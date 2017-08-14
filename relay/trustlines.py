import json
import logging

from web3 import Web3, RPCProvider
from gevent.wsgi import WSGIServer

from relay.node import Node
from relay.graph import CurrencyNetworkGraph
from relay.currency_network import CurrencyNetwork
from relay.logger import getLogger
from relay.app import ApiApp


logger = getLogger('trustlines', logging.DEBUG)


class Trustlines:

    def __init__(self):
        self.currency_network_proxies = {}
        self.currency_network_graphs = {}
        self.config = {}
        self.node = None
        self._web3 = None

    @property
    def networks(self):
        return self.currency_network_proxies.keys()

    def start(self):
        self.load_config()
        self._web3 = Web3(
            RPCProvider(
                self.config['rpc']['host'],
                self.config['rpc']['port'],
                ssl=self.config['rpc']['ssl']
            )
        )
        self.node = Node(self._web3)
        self.load_networks()
        ipport = ('', 5000)
        logger.info('Starting server')
        app = ApiApp(self)
        http_server = WSGIServer(ipport, app, log=None)
        logger.info('Server is running on {}'.format(ipport))
        http_server.serve_forever()

    def load_config(self):
        with open('config.json') as data_file:
            self.config = json.load(data_file)

    def new_network(self, address):
        self.currency_network_graphs[address] = CurrencyNetworkGraph()
        self.currency_network_proxies[address] = CurrencyNetwork(self._web3, None, address)  # TODO load contract abi
        self._start_listen_network(address)

    def load_networks(self):
        for address in self.config['tokens']:
            self.new_network(address)

    def _start_listen_network(self, address):
        graph = self.currency_network_graphs[address]
        proxy = self.currency_network_proxies[address]
        proxy.start_listen_on_full_sync(address, _create_on_full_sync(graph))
        proxy.start_listen_on_balance(address, _create_on_balance(graph))
        proxy.start_listen_on_trustline(address, _create_on_trustline(graph))
        proxy.start_listen_on_transfer(address)


def _create_on_balance(graph):
    def update_balance(a, b, balance):
        graph.update_balance(a, b, balance)

    return update_balance


def _create_on_trustline(graph):
    def update_balance(a, b, balance):
        graph.update_trustline(a, b, balance)

    return update_balance


def _create_on_full_sync(graph):
    def update_community(graph_rep):
        logger.info('Syncing whole graph.. ')
        graph.gen_network(graph_rep)
        logger.info('Syncing whole graph done!')


if __name__ == '__main__':
    trustlines = Trustlines()
    trustlines.start()