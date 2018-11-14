import json
import logging
import os
import sys
import functools
import itertools
from collections import defaultdict
from copy import deepcopy
from typing import Dict, Iterable, List, Union, Optional

import gevent
from eth_utils import is_checksum_address, to_checksum_address
from gevent import sleep
import sqlalchemy
from sqlalchemy.engine.url import URL
from web3 import Web3

from .blockchain.proxy import sorted_events
from relay.pushservice.client import PushNotificationClient
from relay.pushservice.pushservice import FirebaseRawPushService, InvalidClientTokenException
from relay.pushservice.client_token_db import ClientTokenDB, ClientTokenAlreadyExistsException
from relay import ethindex_db
from .blockchain.exchange_proxy import ExchangeProxy
from .blockchain.currency_network_proxy import CurrencyNetworkProxy
from .blockchain import currency_network_events
from .blockchain import token_events
from .blockchain import unw_eth_events
from .blockchain import exchange_events
from .blockchain.node import Node
from .blockchain.token_proxy import TokenProxy
from .blockchain.unw_eth_proxy import UnwEthProxy
from .blockchain.events import BlockchainEvent
from .network_graph.graph import CurrencyNetworkGraph
from .exchange.orderbook import OrderBookGreenlet
from .logger import get_logger
from .streams import Subject, MessagingSubject
from .events import NetworkBalanceEvent, BalanceEvent
import relay.concurrency_utils as concurrency_utils

logger = get_logger('relay', logging.DEBUG)


class TokenNotFoundException(Exception):
    pass


class TrustlinesRelay:

    def __init__(self):
        self.currency_network_proxies: Dict[str, CurrencyNetworkProxy] = {}
        self.currency_network_graphs: Dict[str, CurrencyNetworkGraph] = {}
        self.subjects = defaultdict(Subject)
        self.messaging = defaultdict(MessagingSubject)
        self.config = {}
        self.contracts = {}
        self.node: Node = None
        self._web3 = None
        self.orderbook: OrderBookGreenlet = None
        self.unw_eth_proxies: Dict[str, UnwEthProxy] = {}
        self.token_proxies: Dict[str, TokenProxy] = {}
        self._firebase_raw_push_service: Optional[FirebaseRawPushService] = None
        self._client_token_db: Optional[ClientTokenDB] = None

    @property
    def network_addresses(self) -> Iterable[str]:
        return self.currency_network_proxies.keys()

    @property
    def exchange_addresses(self) -> Iterable[str]:
        return self.orderbook.exchange_addresses

    @property
    def unw_eth_addresses(self) -> Iterable[str]:
        return list(self.unw_eth_proxies)

    @property
    def token_addresses(self) -> Iterable[str]:
        return list(self.token_proxies) + list(self.unw_eth_addresses)

    @property
    def enable_ether_faucet(self) -> bool:
        return self.config.get('enableEtherFaucet', False)

    @property
    def event_query_timeout(self) -> int:
        return self.config.get('eventQueryTimeout', 20)

    @property
    def use_eth_index(self) -> bool:
        return os.environ.get("ETHINDEX", "1") == "1"

    def get_event_selector_for_currency_network(self, network_address):
        """return either a CurrencyNetworkProxy or a EthindexDB instance
        This is being used from relay.api to query for events.
        """
        if self.use_eth_index:
            return ethindex_db.EthindexDB(ethindex_db.connect(""),
                                          address=network_address,
                                          standard_event_types=currency_network_events.standard_event_types,
                                          event_builders=currency_network_events.event_builders,
                                          from_to_types=currency_network_events.from_to_types)
        else:
            return self.currency_network_proxies[network_address]

    def get_event_selector_for_token(self, address):
        """return either a proxy or a EthindexDB instance
        This is being used from relay.api to query for events.
        """
        if self.use_eth_index:
            return ethindex_db.EthindexDB(ethindex_db.connect(""),
                                          address=address,
                                          standard_event_types=token_events.standard_event_types,
                                          event_builders=token_events.event_builders,
                                          from_to_types=token_events.from_to_types)
        else:
            return self.token_proxies[address]

    def get_event_selector_for_unw_eth(self, address):
        """return either a proxy or a EthindexDB instance
        This is being used from relay.api to query for events.
        """
        if self.use_eth_index:
            return ethindex_db.EthindexDB(ethindex_db.connect(""),
                                          address=address,
                                          standard_event_types=unw_eth_events.standard_event_types,
                                          event_builders=unw_eth_events.event_builders,
                                          from_to_types=unw_eth_events.from_to_types)
        else:
            return self.unw_eth_proxies[address]

    def get_event_selector_for_exchange(self, address):
        """return either a proxy or a EthindexDB instance
        This is being used from relay.api to query for events.
        """
        if self.use_eth_index:
            return ethindex_db.EthindexDB(ethindex_db.connect(""),
                                          address=address,
                                          standard_event_types=exchange_events.standard_event_types,
                                          event_builders=exchange_events.event_builders,
                                          from_to_types=exchange_events.from_to_types)
        else:
            return self.orderbook._exchange_proxies[address]

    def is_currency_network(self, address: str) -> bool:
        return address in self.network_addresses

    def is_trusted_token(self, address: str) -> bool:
        return address in self.token_addresses or address in self.unw_eth_addresses

    def get_network_info(self, network_address: str):
        return self.currency_network_proxies[network_address]

    def get_network_infos(self):
        return [self.get_network_info(network_address) for network_address in self.network_addresses]

    def get_users_of_network(self, network_address: str):
        return self.currency_network_graphs[network_address].users

    def start(self):
        self._load_config()
        self._load_contracts()
        self._load_orderbook()
        self._start_push_service()
        url = "{}://{}:{}".format(
            "https" if self.config['rpc']['ssl'] else "http",
            self.config['rpc']['host'],
            self.config['rpc']['port'],
        )
        logger.info('using web3 URL {}'.format(url))
        self._web3 = Web3(
            Web3.HTTPProvider(url)
        )
        self.node = Node(self._web3)
        self._start_listen_on_new_addresses()

    def new_network(self, address: str) -> None:
        assert is_checksum_address(address)
        if address in self.network_addresses:
            return
        logger.info('New network: {}'.format(address))
        self.currency_network_proxies[address] = CurrencyNetworkProxy(self._web3,
                                                                      self.contracts['CurrencyNetwork']['abi'],
                                                                      address)
        self.currency_network_graphs[address] = CurrencyNetworkGraph(
            capacity_imbalance_fee_divisor=self.currency_network_proxies[address].capacity_imbalance_fee_divisor,
            default_interest_rate=self.currency_network_proxies[address].default_interest_rate,
            custom_interests=self.currency_network_proxies[address].custom_interests,
            prevent_mediator_interests=self.currency_network_proxies[address].prevent_mediator_interests
        )
        self._start_listen_network(address)

    def new_exchange(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.exchange_addresses:
            logger.info('New Exchange contract: {}'.format(address))
            self.orderbook.add_exchange(ExchangeProxy(self._web3,
                                                      self.contracts['Exchange']['abi'],
                                                      self.contracts['Token']['abi'],
                                                      address,
                                                      self))

    def new_unw_eth(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.unw_eth_addresses:
            logger.info('New Unwrap ETH contract: {}'.format(address))
            self.unw_eth_proxies[address] = UnwEthProxy(self._web3,
                                                        self.contracts['UnwEth']['abi'],
                                                        address)

    def new_token(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.token_addresses:
            logger.info('New Token contract: {}'.format(address))
            self.token_proxies[address] = TokenProxy(self._web3,
                                                     self.contracts['Token']['abi'],
                                                     address)

    def get_networks_of_user(self, user_address: str) -> List[str]:
        assert is_checksum_address(user_address)
        networks_of_user: List[str] = []
        for network_address in self.network_addresses:
            if user_address in self.currency_network_graphs[network_address].users:
                networks_of_user.append(network_address)
        return networks_of_user

    def add_push_client_token(self, user_address: str, client_token: str) -> None:
        if self._firebase_raw_push_service is not None:
            self._start_pushnotifications(user_address, client_token)
            try:
                if self._client_token_db is not None:
                    self._client_token_db.add_client_token(user_address, client_token)
            except ClientTokenAlreadyExistsException:
                pass  # all good

    def delete_push_client_token(self, user_address: str, client_token: str) -> None:
        if self._firebase_raw_push_service is not None:
            if self._client_token_db is not None:
                self._client_token_db.delete_client_token(user_address, client_token)
            self._stop_pushnotifications(user_address, client_token)

    def _start_pushnotifications(self, user_address: str, client_token: str) -> None:
        assert self._firebase_raw_push_service is not None
        if not self._firebase_raw_push_service.check_client_token(client_token):
            raise InvalidClientTokenException
        for subscription in self.subjects[user_address].subscriptions:
            if (isinstance(subscription.client, PushNotificationClient) and
                    subscription.client.client_token == client_token):
                return  # Token already registered
        logger.debug('Add client token {} for address {}'.format(client_token, user_address))
        client = PushNotificationClient(self._firebase_raw_push_service, client_token)
        self.subjects[user_address].subscribe(
            client
        )
        self.messaging[user_address].subscribe(
            client
        )

    def _stop_pushnotifications(self, user_address: str, client_token: str) -> None:
        success = False
        subscriptions = self.subjects[user_address].subscriptions
        for subscription in subscriptions[:]:  # Copy the list because we will delete items
            if (isinstance(subscription.client, PushNotificationClient) and
                    subscription.client.client_token == client_token):
                logger.debug('Remove client token {} for address {}'.format(client_token, user_address))
                subscription.client.close()
                success = True
        if not success:
            raise TokenNotFoundException

    def get_user_network_events(self,
                                network_address: str,
                                user_address: str,
                                type: str = None,
                                from_block: int = 0
                                ) -> List[BlockchainEvent]:
        proxy = self.get_event_selector_for_currency_network(network_address)
        if type is not None:
            events = proxy.get_network_events(type, user_address,
                                              from_block=from_block,
                                              timeout=self.event_query_timeout)
        else:
            events = proxy.get_all_network_events(user_address,
                                                  from_block=from_block,
                                                  timeout=self.event_query_timeout)
        return events

    def get_network_events(self,
                           network_address: str,
                           type: str = None,
                           from_block: int = 0) -> List[BlockchainEvent]:
        proxy = self.get_event_selector_for_currency_network(network_address)
        if type is not None:
            events = proxy.get_events(type, from_block=from_block, timeout=self.event_query_timeout)
        else:
            events = proxy.get_all_events(from_block=from_block, timeout=self.event_query_timeout)
        return events

    def get_user_events(self,
                        user_address: str,
                        type: str=None,
                        from_block: int=0,
                        timeout: float=None) -> List[BlockchainEvent]:
        assert is_checksum_address(user_address)
        network_event_queries = self._get_network_event_queries(user_address, type, from_block)
        unw_eth_event_queries = self._get_unw_eth_event_queries(user_address, type, from_block)
        exchange_event_queries = self._get_exchange_event_queries(user_address, type, from_block)
        results = concurrency_utils.joinall(network_event_queries +
                                            unw_eth_event_queries +
                                            exchange_event_queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))

    def _get_network_event_queries(self, user_address: str, type: str = None, from_block: int = 0):
        assert is_checksum_address(user_address)
        queries = []
        for network_address in self.network_addresses:
            currency_network_proxy = self.get_event_selector_for_currency_network(network_address)
            if type is not None and type in currency_network_proxy.event_types:
                queries.append(functools.partial(currency_network_proxy.get_network_events,
                                                 type,
                                                 user_address=user_address,
                                                 from_block=from_block))
            else:
                queries.append(functools.partial(currency_network_proxy.get_all_network_events,
                                                 user_address=user_address,
                                                 from_block=from_block))
        return queries

    def _get_unw_eth_event_queries(self, user_address: str, type: str = None, from_block: int = 0):
        assert is_checksum_address(user_address)
        queries = []
        for unw_eth_address in self.unw_eth_addresses:
            unw_eth_proxy = self.get_event_selector_for_unw_eth(unw_eth_address)
            if type is not None and type in unw_eth_proxy.event_types:
                queries.append(functools.partial(unw_eth_proxy.get_unw_eth_events,
                                                 type,
                                                 user_address=user_address,
                                                 from_block=from_block))
            else:
                queries.append(functools.partial(unw_eth_proxy.get_all_unw_eth_events,
                                                 user_address=user_address,
                                                 from_block=from_block))
        return queries

    def _get_exchange_event_queries(self, user_address: str, type: str = None, from_block: int = 0):
        assert is_checksum_address(user_address)
        queries = []
        for exchange_address in self.exchange_addresses:
            exchange_proxy = self.get_event_selector_for_exchange(exchange_address)
            if type is not None and type in exchange_proxy.standard_event_types:
                queries.append(functools.partial(exchange_proxy.get_exchange_events,
                                                 type,
                                                 user_address=user_address,
                                                 from_block=from_block))
            else:
                queries.append(functools.partial(exchange_proxy.get_all_exchange_events,
                                                 user_address=user_address,
                                                 from_block=from_block))
        return queries

    def get_user_token_events(self,
                              token_address: str,
                              user_address: str,
                              type: str = None,
                              from_block: int = 0) -> List[BlockchainEvent]:
        if token_address in self.unw_eth_addresses:
            proxy: Union[UnwEthProxy, TokenProxy] = self.get_event_selector_for_unw_eth(token_address)
            func_names = ['get_unw_eth_events', 'get_all_unw_eth_events']
        else:
            proxy = self.get_event_selector_for_token(token_address)
            func_names = ['get_token_events', 'get_all_token_events']

        if type is not None:
            events = getattr(proxy, func_names[0])(type, user_address, from_block=from_block)
        else:
            events = getattr(proxy, func_names[1])(user_address, from_block=from_block)

        return events

    def get_token_events(self,
                         token_address: str,
                         type: str = None,
                         from_block: int = 0) -> List[BlockchainEvent]:

        if token_address in self.unw_eth_addresses:
            proxy: Union[UnwEthProxy, TokenProxy] = self.get_event_selector_for_unw_eth(
                token_address)
        else:
            proxy = self.get_event_selector_for_token(token_address)

        if type is not None:
            events = proxy.get_events(type, from_block=from_block)
        else:
            events = proxy.get_all_events(from_block=from_block)

        return events

    def get_exchange_events(self,
                            exchange_address: str,
                            type: str = None,
                            from_block: int = 0) -> List[BlockchainEvent]:
        proxy = self.get_event_selector_for_exchange(exchange_address)
        if type is not None:
            events = proxy.get_events(type, from_block=from_block)
        else:
            events = proxy.get_all_events(from_block=from_block)
        return events

    def get_user_exchange_events(self,
                                 exchange_address: str,
                                 user_address: str,
                                 type: str = None,
                                 from_block: int = 0) -> List[BlockchainEvent]:
        proxy = self.get_event_selector_for_exchange(exchange_address)
        if type is not None:
            events = proxy.get_exchange_events(type,
                                               user_address,
                                               from_block=from_block,
                                               timeout=self.event_query_timeout)
        else:
            events = proxy.get_all_exchange_events(user_address,
                                                   from_block=from_block,
                                                   timeout=self.event_query_timeout)
        return events

    def get_all_user_exchange_events(self,
                                     user_address: str,
                                     type: str=None,
                                     from_block: int=0,
                                     timeout: float=None) -> List[BlockchainEvent]:
        assert is_checksum_address(user_address)
        exchange_event_queries = self._get_exchange_event_queries(user_address, type, from_block)
        results = concurrency_utils.joinall(exchange_event_queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))

    def _load_config(self):
        with open('config.json') as data_file:
            self.config = json.load(data_file)

    def _load_contracts(self):
        with open(os.path.join(sys.prefix, 'trustlines-contracts', 'build', 'contracts.json')) as data_file:
            self.contracts = json.load(data_file)

    def _load_orderbook(self):
        self.orderbook = OrderBookGreenlet()
        self.orderbook.connect_db(engine=create_engine())
        self.orderbook.start()

    def _load_addresses(self):
        addresses = {}
        with open('addresses.json') as data_file:
            content = data_file.read()
            if content:
                try:
                    addresses = json.loads(content)
                except json.decoder.JSONDecodeError as e:
                    logger.error('Could not read addresses.json:' + str(e))
            else:
                logger.warning('addresses.json file is empty')
        network_addresses = addresses.get('networks', [])
        for address in network_addresses:
            self.new_network(to_checksum_address(address))
        exchange_address = addresses.get('exchange', None)
        if exchange_address is not None:
            self.new_exchange(to_checksum_address(exchange_address))
        new_unw_eth_address = addresses.get('unwEth', None)
        if new_unw_eth_address is not None:
            self.new_unw_eth(to_checksum_address(new_unw_eth_address))

    def _start_listen_network(self, address):
        assert is_checksum_address(address)
        graph = self.currency_network_graphs[address]
        proxy = self.currency_network_proxies[address]
        proxy.start_listen_on_full_sync(_create_on_full_sync(graph), self.config.get('syncInterval', 300))
        proxy.start_listen_on_balance(self._process_balance_update)
        proxy.start_listen_on_trustline(self._process_trustline_update)
        proxy.start_listen_on_transfer(self._process_transfer)
        proxy.start_listen_on_trustline_request(self._process_trustline_request)

    def _start_listen_on_new_addresses(self):
        def listen():
            while True:
                try:
                    self._load_addresses()
                except Exception:
                    logger.critical("Error while loading addresses", exc_info=sys.exc_info())
                sleep(self.config.get('updateNetworksInterval', 120))

        gevent.Greenlet.spawn(listen)

    def _start_push_service(self):
        path = self.config.get('firebase', {}).get('credentialsPath', None)
        if path is not None:
            self._firebase_raw_push_service = FirebaseRawPushService(path)
            self._client_token_db = ClientTokenDB(engine=create_engine())
            logger.info('Firebase pushservice started')
            self._start_pushnotifications_for_registered_users()
        else:
            logger.info('No firebase credentials in config, pushservice disabled')

    def _start_pushnotifications_for_registered_users(self):
        number_of_new_listeners = 0
        for token_mapping in self._client_token_db.get_all_client_tokens():
            try:
                self._start_pushnotifications(token_mapping.user_address, token_mapping.client_token)
                number_of_new_listeners += 1
            except InvalidClientTokenException:
                # token now invalid, so delete it from database
                self._client_token_db.delete_client_token(token_mapping.user_address, token_mapping.client_token)
                pass
        logger.debug('Start pushnotifications for {} registered user devices'.format(number_of_new_listeners))

    def _process_balance_update(self, balance_update_event):
        graph = self.currency_network_graphs[balance_update_event.network_address]
        graph.update_balance(balance_update_event.from_,
                             balance_update_event.to,
                             balance_update_event.value,
                             balance_update_event.timestamp)
        self._publish_balance_event(balance_update_event.from_, balance_update_event.to,
                                    balance_update_event.network_address)
        self._publish_balance_event(balance_update_event.to, balance_update_event.from_,
                                    balance_update_event.network_address)
        self._publish_network_balance_event(balance_update_event.from_, balance_update_event.network_address)
        self._publish_network_balance_event(balance_update_event.to, balance_update_event.network_address)

    def _process_transfer(self, transfer_event):
        self._publish_blockchain_event(transfer_event)

    def _process_trustline_request(self, trustline_request_event):
        logger.debug('Process trustline request event')
        self._publish_blockchain_event(trustline_request_event)

    def _process_trustline_update(self, trustline_update_event):
        logger.debug('Process trustline update event')
        graph = self.currency_network_graphs[trustline_update_event.network_address]
        graph.update_trustline(creditor=trustline_update_event.from_,
                               debtor=trustline_update_event.to,
                               creditline_given=trustline_update_event.creditline_given,
                               creditline_received=trustline_update_event.creditline_received,
                               interest_rate_given=trustline_update_event.interest_rate_given,
                               interest_rate_received=trustline_update_event.interest_rate_received,
                               timestamp=trustline_update_event.timestamp
                               )
        self._publish_blockchain_event(trustline_update_event)
        self._publish_balance_event(trustline_update_event.from_, trustline_update_event.to,
                                    trustline_update_event.network_address)
        self._publish_balance_event(trustline_update_event.to, trustline_update_event.from_,
                                    trustline_update_event.network_address)
        self._publish_network_balance_event(trustline_update_event.from_, trustline_update_event.network_address)
        self._publish_network_balance_event(trustline_update_event.to, trustline_update_event.network_address)

    def _publish_blockchain_event(self, event):
        event2 = deepcopy(event)
        event.user = event.from_
        event2.user = event2.to
        self._publish_user_event(event)
        self._publish_user_event(event2)

    def _publish_user_event(self, event):
        assert event.user is not None
        self.subjects[event.user].publish(event)

    def _publish_network_balance_event(self, user, network_address):
        graph = self.currency_network_graphs[network_address]
        summary = graph.get_account_sum(user)
        self._publish_user_event(NetworkBalanceEvent(network_address, user, summary))

    def _publish_balance_event(self, from_, to, network_address):
        graph = self.currency_network_graphs[network_address]
        summary = graph.get_account_sum(from_, to)
        self._publish_user_event(BalanceEvent(network_address, from_, to, summary))


def _create_on_full_sync(graph):
    def update_community(graph_rep):
        graph.gen_network(graph_rep)

    return update_community


def create_engine():
    return sqlalchemy.create_engine(URL(drivername='postgresql',
                                    database=os.environ.get("PGDATABASE", ""),
                                    host=os.environ.get("PGHOST", ""),
                                    username=os.environ.get("PGUSER", ""),
                                    password=os.environ.get("PGPASSWORD", "")))
