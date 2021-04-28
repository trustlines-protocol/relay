import json
import logging
import os
import sys
from collections import defaultdict
from copy import deepcopy
from enum import Enum
from typing import Dict, Iterable, List, NamedTuple, Optional, Set, Union, cast

import eth_account
import eth_keyfile
import gevent
import sqlalchemy
from eth_utils import is_checksum_address, to_checksum_address
from sqlalchemy.engine.url import URL
from tlbin import load_packaged_contracts, load_packaged_merged_abis
from tldeploy.identity import MetaTransaction
from web3 import Web3

from relay import signing_middleware
from relay.blockchain.identity_events import FeePaymentEventType
from relay.blockchain.identity_proxy import IdentityProxy
from relay.blockchain.proxy import LogFilterListener
from relay.ethindex_db import ethindex_db
from relay.ethindex_db.sync_updates import (
    BalanceUpdateFeedUpdate,
    FeedUpdate,
    TrustlineUpdateFeedUpdate,
    graph_update_getter,
)
from relay.pushservice.client import PushNotificationClient
from relay.pushservice.client_token_db import (
    ClientTokenAlreadyExistsException,
    ClientTokenDB,
)
from relay.pushservice.pushservice import (
    FirebaseRawPushService,
    InvalidClientTokenException,
    create_firebase_app_from_path_to_keyfile,
)
from relay.web3provider import create_provider_from_config

from .blockchain import (
    currency_network_events,
    exchange_events,
    token_events,
    unw_eth_events,
)
from .blockchain.currency_network_proxy import CurrencyNetworkProxy
from .blockchain.delegate import Delegate, DelegationFees
from .blockchain.events import BlockchainEvent
from .blockchain.exchange_proxy import ExchangeProxy
from .blockchain.node import Node
from .blockchain.token_proxy import TokenProxy
from .blockchain.unw_eth_proxy import UnwEthProxy
from .ethindex_db.events_informations import EventsInformationFetcher
from .events import BalanceEvent, NetworkBalanceEvent
from .exchange.orderbook import OrderBookGreenlet
from .network_graph.graph import CurrencyNetworkGraph
from .streams import MessagingSubject, Subject

logger = logging.getLogger("relay")


class TokenNotFoundException(Exception):
    pass


class NetworkInfo(NamedTuple):
    address: str
    name: str
    symbol: str
    decimals: int
    num_users: int
    capacity_imbalance_fee_divisor: int
    default_interest_rate: int
    custom_interests: bool
    prevent_mediator_interests: bool
    interest_rate_decimals: int
    is_frozen: bool


class ContractTypes(Enum):
    CURRENCY_NETWORK = "CurrencyNetwork"
    EXCHANGE = "Exchange"
    UNWETH = "UnwETH"
    TOKEN = "Token"


all_standard_event_types = (
    currency_network_events.standard_event_types
    + exchange_events.standard_event_types
    + unw_eth_events.standard_event_types
    + token_events.standard_event_types
)
all_event_builders: Dict[str, BlockchainEvent] = {}
all_from_to_types: Dict[str, List[str]] = {}
all_event_contract_types = [contract_type.value for contract_type in ContractTypes]
for contract_type, contract in [
    (ContractTypes.CURRENCY_NETWORK, currency_network_events),
    (ContractTypes.EXCHANGE, exchange_events),
    (ContractTypes.UNWETH, unw_eth_events),
    (ContractTypes.TOKEN, token_events),
]:
    for key, value in contract.event_builders.items():  # type: ignore
        key = contract_type.value + key
        assert key not in all_event_builders
        all_event_builders[key] = value
    for key, value in contract.from_to_types.items():  # type: ignore
        key = contract_type.value + key
        assert key not in all_from_to_types
        all_from_to_types[key] = value


class TrustlinesRelay:
    def __init__(self, config, addresses_json_path="addresses.json"):
        self.config = config
        self.addresses_json_path = addresses_json_path
        self.currency_network_proxies: Dict[str, CurrencyNetworkProxy] = {}
        self.currency_network_graphs: Dict[str, CurrencyNetworkGraph] = {}
        self.subjects = defaultdict(Subject)
        self.messaging = defaultdict(MessagingSubject)
        self.contracts = {}
        self.node: Node = None
        self._web3 = None
        self.orderbook: OrderBookGreenlet = None
        self.unw_eth_proxies: Dict[str, UnwEthProxy] = {}
        self.token_proxies: Dict[str, TokenProxy] = {}
        self._firebase_raw_push_service: Optional[FirebaseRawPushService] = None
        self._client_token_db: Optional[ClientTokenDB] = None
        self.fixed_gas_price: Optional[int] = None
        self.known_identity_factories: List[str] = []
        self._log_listener = None

    @property
    def network_addresses(self) -> Iterable[str]:
        return self.currency_network_proxies.keys()

    @property
    def exchange_addresses(self) -> Iterable[str]:
        if self.orderbook is not None:
            return self.orderbook.exchange_addresses
        else:
            return []

    @property
    def unw_eth_addresses(self) -> Iterable[str]:
        return list(self.unw_eth_proxies)

    @property
    def token_addresses(self) -> Iterable[str]:
        return list(self.token_proxies) + list(self.unw_eth_addresses)

    @property
    def enable_ether_faucet(self) -> bool:
        return self.config["faucet"]["enable"]

    @property
    def enable_relay_meta_transaction(self) -> bool:
        return self.config["delegate"]["enable"]

    @property
    def enable_deploy_identity(self) -> bool:
        return self.config["delegate"]["enable_deploy_identity"]

    def get_ethindex_db_for_currency_network(
        self, network_address: Optional[str] = None
    ) -> ethindex_db.CurrencyNetworkEthindexDB:
        """return an EthindexDB instance.
        This is being used from relay.api to query for events.
        """
        address_to_contract_types: Dict[str, str] = {}
        for address in self.network_addresses:
            address_to_contract_types[address] = ContractTypes.CURRENCY_NETWORK.value

        return ethindex_db.CurrencyNetworkEthindexDB(
            ethindex_db.connect(""),
            address=network_address,
            standard_event_types=currency_network_events.standard_event_types,
            event_builders=all_event_builders,
            from_to_types=currency_network_events.from_to_types,
            address_to_contract_types=address_to_contract_types,
        )

    def get_ethindex_db_for_token(self, address: str):
        """return an EthindexDB instance
        This is being used from relay.api to query for events.
        """
        return ethindex_db.EthindexDB(
            ethindex_db.connect(""),
            address=address,
            standard_event_types=token_events.standard_event_types,
            event_builders=token_events.event_builders,
            from_to_types=token_events.from_to_types,
        )

    def get_ethindex_db_for_unw_eth(self, address: str):
        """return an EthindexDB instance
        This is being used from relay.api to query for events.
        """
        return ethindex_db.EthindexDB(
            ethindex_db.connect(""),
            address=address,
            standard_event_types=unw_eth_events.standard_event_types,
            event_builders=unw_eth_events.event_builders,
            from_to_types=unw_eth_events.from_to_types,
        )

    def get_ethindex_db_for_exchange(self, address: Optional[str] = None):
        """return an EthindexDB instance
        This is being used from relay.api to query for events.
        """
        return ethindex_db.ExchangeEthindexDB(
            ethindex_db.connect(""),
            address=address,
            standard_event_types=exchange_events.standard_event_types,
            event_builders=exchange_events.event_builders,
            from_to_types=exchange_events.from_to_types,
        )

    def is_currency_network(self, address: str) -> bool:
        return address in self.network_addresses

    def is_currency_network_frozen(self, address: str) -> bool:
        return self.currency_network_graphs[address].is_frozen

    def is_trusted_token(self, address: str) -> bool:
        return address in self.token_addresses or address in self.unw_eth_addresses

    def get_network_info(self, network_address: str) -> NetworkInfo:
        proxy = self.currency_network_proxies[network_address]
        graph = self.currency_network_graphs[network_address]
        assert (
            proxy.address is not None
        ), "Invalid currency network proxy with no address."
        return NetworkInfo(
            address=proxy.address,
            name=proxy.name,
            symbol=proxy.symbol,
            decimals=proxy.decimals,
            num_users=len(graph.users),
            capacity_imbalance_fee_divisor=proxy.capacity_imbalance_fee_divisor,
            default_interest_rate=proxy.default_interest_rate,
            custom_interests=proxy.custom_interests,
            prevent_mediator_interests=proxy.prevent_mediator_interests,
            interest_rate_decimals=proxy.interest_rate_decimals,
            is_frozen=graph.is_frozen,
        )

    def get_network_infos(self) -> List[NetworkInfo]:
        return [
            self.get_network_info(network_address)
            for network_address in self.network_addresses
        ]

    def get_users_of_network(self, network_address: str):
        return self.currency_network_graphs[network_address].users

    def get_friends_of_user_in_network(self, network_address: str, user_address: str):
        return self.currency_network_graphs[network_address].get_friends(user_address)

    def get_list_of_accrued_interests_for_trustline(
        self,
        network_address: str,
        user_address: str,
        counterparty_address: str,
        start_time: int = 0,
        end_time: int = None,
    ):
        event_selector = self.get_ethindex_db_for_currency_network(network_address)
        return EventsInformationFetcher(
            event_selector
        ).get_list_of_paid_interests_for_trustline_in_between_timestamps(
            network_address, user_address, counterparty_address, start_time, end_time
        )

    def get_total_sum_transferred(
        self,
        network_address,
        sender_address,
        receiver_address,
        start_time=0,
        end_time=None,
    ):
        event_selector = self.get_ethindex_db_for_currency_network(network_address)
        return EventsInformationFetcher(event_selector).get_total_sum_transferred(
            sender_address, receiver_address, start_time, end_time
        )

    def get_transfer_information_for_tx_hash(self, tx_hash: str):
        fetcher = EventsInformationFetcher(self.get_ethindex_db_for_currency_network())
        return fetcher.get_transfer_details_for_tx(tx_hash)

    def get_transfer_information_from_event_id(self, block_hash, log_index):
        fetcher = EventsInformationFetcher(self.get_ethindex_db_for_currency_network())
        return fetcher.get_transfer_details_for_id(block_hash, log_index)

    def get_paid_delegation_fees_for_tx_hash(self, tx_hash):
        event_proxy = IdentityProxy(self._web3, abi=self.contracts["Identity"]["abi"])
        return event_proxy.get_transaction_events(
            tx_hash, event_types=FeePaymentEventType
        )

    def get_earned_mediation_fees(
        self,
        network_address,
        user_address,
        start_time: int = 0,
        end_time: Optional[int] = None,
    ):
        current_network_graph = self.currency_network_graphs[network_address]
        empty_graph = CurrencyNetworkGraph(
            capacity_imbalance_fee_divisor=current_network_graph.capacity_imbalance_fee_divisor,
            default_interest_rate=current_network_graph.default_interest_rate,
            custom_interests=current_network_graph.custom_interests,
            prevent_mediator_interests=current_network_graph.prevent_mediator_interests,
        )
        event_selector = self.get_ethindex_db_for_currency_network(network_address)
        return EventsInformationFetcher(
            event_selector
        ).get_earned_mediation_fees_in_between_timestamps(
            user_address, empty_graph, start_time, end_time
        )

    def get_debt_list_of_user(self, user_address):

        event_selector = self.get_ethindex_db_for_currency_network()
        return EventsInformationFetcher(
            event_selector
        ).get_debt_lists_in_all_networks_with_path(
            user_address, currency_network_graphs=self.currency_network_graphs
        )

    def deploy_identity(self, factory_address, implementation_address, signature):
        return self.delegate.deploy_identity(
            factory_address, implementation_address, signature
        )

    def delegate_meta_transaction(self, meta_transaction: MetaTransaction):
        return self.delegate.send_signed_meta_transaction(meta_transaction)

    def get_meta_transaction_status(self, identity_address, hash):
        return self.delegate.get_meta_transaction_status(identity_address, hash)

    def meta_transaction_fees(self, meta_transaction: MetaTransaction):
        return self.delegate.calculate_fees_for_meta_transaction(meta_transaction)

    def get_identity_info(self, identity_address: str):
        return {
            "balance": self.node.balance(identity_address),
            "identity": identity_address,
            "nextNonce": self.delegate.calc_next_nonce(identity_address),
            "implementationAddress": self.delegate.get_implementation_address(
                identity_address
            ),
        }

    def _install_w3_middleware(self):
        """install signing middleware if an account is configured"""
        if "account" not in self.config:
            logger.warning("No account configured")
            return

        keystore_path = self.config["account"]["keystore_path"]
        keystore_password_path = self.config["account"]["keystore_password_path"]
        with open(keystore_password_path, "r") as password_file:
            password = password_file.readline().strip()

        try:
            private_key = eth_keyfile.extract_key_from_keyfile(
                keystore_path, password.encode("utf-8")
            )
        except ValueError:
            raise ValueError(
                "Could not decrypt keystore. Please make sure the password is correct."
            )

        account = eth_account.Account.from_key(private_key)
        signing_middleware.install_signing_middleware(self._web3, account)
        logger.info(
            f"private key for address {account.address} loaded for signing transactions"
        )

    def _make_w3(self):
        """create and set the w3 object as self._web3"""
        rpc_config = self.config["node_rpc"]
        self._web3 = Web3(create_provider_from_config(rpc_config))

    def _start_delegate(self):
        default_fee_recipient = self._web3.eth.defaultAccount or self.node.address
        delegation_fees = [
            DelegationFees(
                fee_recipient=d.get("fee_recipient", default_fee_recipient),
                base_fee=d["base_fee"],
                gas_price=d["gas_price"],
                currency_network_of_fees=d["currency_network"],
            )
            for d in self.config["delegate"]["fees"]
            if d
        ]
        logger.info(f"Started delegate with delegation fees: {delegation_fees}")
        self.delegate = Delegate(
            self._web3,
            default_fee_recipient,
            self.contracts["Identity"]["abi"],
            self.known_identity_factories,
            delegation_fees=delegation_fees,
            config=self.config["delegate"],
        )

    def start(self):
        self._load_gas_price_settings(self.config["relay"]["gas_price_computation"])
        self.contracts = load_packaged_contracts()
        if self.config["exchange"]["enable"]:
            self._load_orderbook()
        if self.config["push_notification"]["enable"]:
            self._start_push_service()
        self._make_w3()
        self._install_w3_middleware()
        self.node = Node(self._web3, fixed_gas_price=self.fixed_gas_price)
        self._log_listener = LogFilterListener(self._web3)
        if self.config["delegate"]["enable"]:
            self._start_delegate()
        self._load_addresses()
        self._start_sync_graphs_via_feed()

    def _start_sync_graphs_via_feed(self):
        conn = ethindex_db.connect("")
        updates_getter = graph_update_getter()

        def sync():
            while True:
                graph_updates = updates_getter(conn)
                self._apply_feed_update_on_graph(graph_updates)
                self._publish_feed_update_events(graph_updates)
                gevent.sleep(self.config["trustline_index"]["sync_interval"])

        greenlet = gevent.Greenlet.spawn(sync)
        greenlet.link_exception(lambda *args: sys.exit("Graph sync greenlet died"))

    def new_network(self, address: str) -> None:
        assert is_checksum_address(address)
        if address in self.network_addresses:
            return
        logger.info("New network: {}".format(address))
        self.currency_network_proxies[address] = CurrencyNetworkProxy(
            self._web3,
            load_packaged_merged_abis()["MergedCurrencyNetworksAbi"]["abi"],
            address,
        )
        currency_network_proxy = self.currency_network_proxies[address]
        self.currency_network_graphs[address] = CurrencyNetworkGraph(
            capacity_imbalance_fee_divisor=currency_network_proxy.capacity_imbalance_fee_divisor,
            default_interest_rate=currency_network_proxy.default_interest_rate,
            custom_interests=currency_network_proxy.custom_interests,
            prevent_mediator_interests=currency_network_proxy.prevent_mediator_interests,
        )
        self._log_listener.add_proxy(currency_network_proxy)
        self.fully_sync_graph(address)
        self._start_listen_network(address)

    def fully_sync_graph(self, address):
        logger.info(f"Fully syncing graph from blockchain state for address: {address}")

        self.currency_network_graphs[address].gen_network(
            self.currency_network_proxies[address].gen_graph_representation()
        )
        self.currency_network_graphs[address].is_frozen = self.currency_network_proxies[
            address
        ].fetch_is_frozen_status()

        logger.info(f"Graph fully synced for address: {address}")

    def new_exchange(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.exchange_addresses:
            logger.info("New Exchange contract: {}".format(address))
            if self.orderbook is not None:
                proxy = ExchangeProxy(
                    self._web3,
                    self.contracts["Exchange"]["abi"],
                    self.contracts["Token"]["abi"],
                    address,
                    self,
                )
                self.orderbook.add_exchange(proxy)
            else:
                raise ValueError("Exchange address given but no orderbook loaded")

    def new_unw_eth(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.unw_eth_addresses:
            logger.info("New Unwrap ETH contract: {}".format(address))
            proxy = UnwEthProxy(self._web3, self.contracts["UnwEth"]["abi"], address)
            self.unw_eth_proxies[address] = proxy

    def new_token(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.token_addresses:
            logger.info("New Token contract: {}".format(address))
            proxy = TokenProxy(self._web3, self.contracts["Token"]["abi"], address)
            self.token_proxies[address] = proxy

    def new_known_factory(self, address: str) -> None:
        assert is_checksum_address(address)
        if address not in self.known_identity_factories:
            logger.info("New identity factory contract: {}".format(address))
            self.known_identity_factories.append(address)

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
            if (
                isinstance(subscription.client, PushNotificationClient)
                and subscription.client.client_token == client_token
            ):
                return  # Token already registered
        logger.debug(
            "Add client token {} for address {}".format(client_token, user_address)
        )
        client = PushNotificationClient(self._firebase_raw_push_service, client_token)
        self.subjects[user_address].subscribe(client)
        # Silent: Do not mark notifications as read, so that we can query them later
        self.messaging[user_address].subscribe(client, silent=True)

    def _stop_pushnotifications(self, user_address: str, client_token: str) -> None:
        success = False
        subscriptions = self.subjects[user_address].subscriptions

        # Copy the list because we will delete items while iterating over it
        for subscription in subscriptions[:]:
            if (
                isinstance(subscription.client, PushNotificationClient)
                and subscription.client.client_token == client_token
            ):
                logger.debug(
                    "Remove client token {} for address {}".format(
                        client_token, user_address
                    )
                )
                subscription.client.close()
                success = True
        if not success:
            raise TokenNotFoundException

    def get_user_network_events(
        self,
        network_address: str,
        user_address: str,
        type: str = None,
        from_block: int = 0,
    ) -> List[BlockchainEvent]:
        ethindex_db = self.get_ethindex_db_for_currency_network(network_address)
        if type is not None:
            events = ethindex_db.get_network_events(
                type, user_address, from_block=from_block,
            )
        else:
            events = ethindex_db.get_all_network_events(
                user_address, from_block=from_block
            )
        return events

    def get_trustline_events(
        self,
        network_address: str,
        user_address: str,
        counterparty_address: str,
        type: str = None,
        from_block: int = 0,
    ):
        if type is None:
            event_types = None
        else:
            event_types = [type]

        ethindex = ethindex_db.CurrencyNetworkEthindexDB(
            ethindex_db.connect(""),
            address=network_address,
            standard_event_types=currency_network_events.trustline_event_types,
            event_builders=currency_network_events.event_builders,
            from_to_types=currency_network_events.from_to_types,
        )

        events = ethindex.get_trustline_events(
            network_address,
            user_address,
            counterparty_address,
            event_types,
            from_block=from_block,
        )
        return events

    def get_network_events(
        self, network_address: str, type: str = None, from_block: int = 0
    ) -> List[BlockchainEvent]:
        ethindex_db = self.get_ethindex_db_for_currency_network(network_address)
        if type is not None:
            events = ethindex_db.get_events(type, from_block=from_block)
        else:
            events = ethindex_db.get_all_events(from_block=from_block)
        return events

    def get_user_events(
        self,
        user_address: str,
        event_type: str = None,
        from_block: int = 0,
        contract_type: ContractTypes = None,
    ) -> List[BlockchainEvent]:
        """
        Get all events of users for user_address.
        Filter with from_block, event_type and contract_type
        """
        assert is_checksum_address(user_address)
        event_types: Optional[List[str]]
        if event_type:
            event_types = [event_type]
        else:
            event_types = None

        address_to_contract_types: Dict[str, str] = {}

        if contract_type == ContractTypes.CURRENCY_NETWORK or contract_type is None:
            for address in self.network_addresses:
                address_to_contract_types[
                    address
                ] = ContractTypes.CURRENCY_NETWORK.value
        if contract_type == ContractTypes.EXCHANGE or contract_type is None:
            for address in self.exchange_addresses:
                address_to_contract_types[address] = ContractTypes.EXCHANGE.value
        if contract_type == ContractTypes.TOKEN or contract_type is None:
            for address in self.token_addresses:
                address_to_contract_types[address] = ContractTypes.TOKEN.value
        if contract_type == ContractTypes.UNWETH or contract_type is None:
            for address in self.unw_eth_addresses:
                address_to_contract_types[address] = ContractTypes.UNWETH.value

        ethindex = ethindex_db.EthindexDB(
            ethindex_db.connect(""),
            standard_event_types=all_standard_event_types,
            event_builders=all_event_builders,
            from_to_types=all_from_to_types,
            address_to_contract_types=address_to_contract_types,
        )
        return ethindex.get_all_contract_events(
            event_types, user_address=user_address, from_block=from_block,
        )

    def get_user_token_events(
        self,
        token_address: str,
        user_address: str,
        type: str = None,
        from_block: int = 0,
    ) -> List[BlockchainEvent]:

        if token_address in self.unw_eth_addresses:
            ethindex_db = self.get_ethindex_db_for_unw_eth(token_address)
        else:
            ethindex_db = self.get_ethindex_db_for_token(token_address)

        if type is not None:
            events = getattr(ethindex_db, "get_user_events")(
                event_type=type, user_address=user_address, from_block=from_block
            )
        else:
            events = getattr(ethindex_db, "get_all_contract_events")(
                user_address=user_address, from_block=from_block
            )

        return events

    def get_token_events(
        self, token_address: str, type: str = None, from_block: int = 0
    ) -> List[BlockchainEvent]:

        if token_address in self.unw_eth_addresses:
            ethindex_db = self.get_ethindex_db_for_unw_eth(token_address)
        else:
            ethindex_db = self.get_ethindex_db_for_token(token_address)

        if type is not None:
            events = ethindex_db.get_events(type, from_block=from_block)
        else:
            events = ethindex_db.get_all_events(from_block=from_block)

        return events

    def get_exchange_events(
        self, exchange_address: str, type: str = None, from_block: int = 0
    ) -> List[BlockchainEvent]:
        ethindex_db = self.get_ethindex_db_for_exchange(exchange_address)
        if type is not None:
            events = ethindex_db.get_events(type, from_block=from_block)
        else:
            events = ethindex_db.get_all_events(from_block=from_block)
        return events

    def get_user_exchange_events(
        self,
        exchange_address: str,
        user_address: str,
        type: str = None,
        from_block: int = 0,
    ) -> List[BlockchainEvent]:
        ethindex_db = self.get_ethindex_db_for_exchange(exchange_address)
        if type is not None:
            events = ethindex_db.get_user_events(
                event_type=type, user_address=user_address, from_block=from_block,
            )
        else:
            events = ethindex_db.get_all_contract_events(
                user_address=user_address, from_block=from_block,
            )
        return events

    def get_all_user_exchange_events(
        self, user_address: str, type: str = None, from_block: int = 0,
    ) -> List[BlockchainEvent]:
        assert is_checksum_address(user_address)

        exchange_ethindex = self.get_ethindex_db_for_exchange()
        return exchange_ethindex.get_all_exchange_events_of_user(
            user_address=user_address,
            all_exchange_addresses=self.exchange_addresses,
            type=type,
            from_block=from_block,
        )

    def _apply_feed_update_on_graph(
        self, feed_update: Iterable[FeedUpdate],
    ):
        for update in feed_update:
            if update.address not in self.currency_network_graphs.keys():
                logger.warning(f"Got event_feed with unknown network address {update}")
                continue

            graph = self.currency_network_graphs[update.address]
            graph.update_from_feed(update)

    def _publish_feed_update_events(
        self, feed_update: Iterable[FeedUpdate],
    ):
        # We want to publish only the latest update for each user / trustline
        feed_update = sorted(
            feed_update, key=lambda update: update.timestamp, reverse=True
        )

        def unique_trustline_id(from_, to, network_address):
            if from_ > to:
                return from_ + to + network_address
            else:
                return to + from_ + network_address

        processed_trusline_updates: Set[str] = set()
        processed_user_updates: Set[str] = set()

        for update in feed_update:
            if update.address not in self.currency_network_graphs.keys():
                continue

            if type(update) in [TrustlineUpdateFeedUpdate, BalanceUpdateFeedUpdate]:
                update = cast(
                    Union[TrustlineUpdateFeedUpdate, BalanceUpdateFeedUpdate], update
                )

                trustline_id = unique_trustline_id(
                    update.from_, update.to, update.address
                )
                if trustline_id not in processed_trusline_updates:
                    self._publish_trustline_events(
                        user1=update.from_,
                        user2=update.to,
                        network_address=update.address,
                        timestamp=update.timestamp,
                    )
                    processed_trusline_updates.add(trustline_id)

                for user in [update.from_, update.to]:
                    if user not in processed_user_updates:
                        self._publish_network_balance_event(
                            user=user,
                            network_address=update.address,
                            timestamp=update.timestamp,
                        )
                        processed_user_updates.add(user)

    def _load_gas_price_settings(self, gas_price_settings: Dict):
        method = gas_price_settings["method"]
        methods = ["fixed", "rpc"]
        if method not in methods:
            raise ValueError(
                f"Given gasprice computation method: {method} must be on of {methods}"
            )

        if method == "fixed":
            logger.info(f"Set gasprice method to {method}")
            fixed_gas_price = gas_price_settings.get("gasPrice", 0)
            if not isinstance(fixed_gas_price, int) or fixed_gas_price < 0:
                raise ValueError(
                    f"Given gasprice: {fixed_gas_price} must be a non negative integer"
                )
            self.fixed_gas_price = fixed_gas_price

    def _load_orderbook(self):
        logger.info("Start exchange orderbook")
        self.orderbook = OrderBookGreenlet()
        self.orderbook.connect_db(engine=create_engine())
        self.orderbook.start()

    def _load_addresses(self):
        addresses = {}
        with open(self.addresses_json_path) as data_file:
            content = data_file.read()
            if content:
                try:
                    addresses = json.loads(content)
                except json.decoder.JSONDecodeError as e:
                    logger.error("Could not read addresses.json:" + str(e))
            else:
                logger.warning(f"{self.addresses_json_path} file is empty")
        network_addresses = addresses.get("networks", [])
        for address in network_addresses:
            self.new_network(to_checksum_address(address))
        exchange_address = addresses.get("exchange", None)
        if exchange_address is not None:
            self.new_exchange(to_checksum_address(exchange_address))
        new_unw_eth_address = addresses.get("unwEth", None)
        if new_unw_eth_address is not None:
            self.new_unw_eth(to_checksum_address(new_unw_eth_address))
        known_factories = addresses.get("identityProxyFactory", [])
        if type(known_factories) is list:
            for address in known_factories:
                self.new_known_factory(address)
        else:
            self.new_known_factory(known_factories)

        self._log_listener.start()

    def _start_listen_network(self, address):
        assert is_checksum_address(address)
        proxy = self.currency_network_proxies[address]
        proxy.start_listen_on_trustline(
            self._process_trustline_update, start_log_filter=False
        )
        proxy.start_listen_on_transfer(self._process_transfer, start_log_filter=False)
        proxy.start_listen_on_trustline_request(
            self._process_trustline_request, start_log_filter=False
        )
        proxy.start_listen_on_trustline_request_cancel(
            self._process_trustline_request_cancel, start_log_filter=False
        )

    def _start_push_service(self):
        logger.info("Start pushnotification service")
        path = self.config["push_notification"]["firebase_credentials_path"]
        app = create_firebase_app_from_path_to_keyfile(path)
        self._firebase_raw_push_service = FirebaseRawPushService(app)
        self._client_token_db = ClientTokenDB(engine=create_engine())
        logger.info("Firebase pushservice started")
        self._start_pushnotifications_for_registered_users()

    def _start_pushnotifications_for_registered_users(self):
        number_of_new_listeners = 0
        for token_mapping in self._client_token_db.get_all_client_tokens():
            try:
                self._start_pushnotifications(
                    token_mapping.user_address, token_mapping.client_token
                )
                number_of_new_listeners += 1
            except InvalidClientTokenException:
                # token now invalid, so delete it from database
                self._client_token_db.delete_client_token(
                    token_mapping.user_address, token_mapping.client_token
                )
                pass
        logger.debug(
            "Start pushnotifications for {} registered user devices".format(
                number_of_new_listeners
            )
        )

    def _process_transfer(self, transfer_event):
        self._publish_blockchain_event(transfer_event)

    def _process_trustline_request(self, trustline_request_event):
        logger.debug("Process trustline request event: %s", trustline_request_event)
        self._publish_blockchain_event(trustline_request_event)

    def _process_trustline_request_cancel(self, trustline_request_cancel_event):
        logger.debug(
            "Process trustline request cancel event: %s", trustline_request_cancel_event
        )
        self._publish_blockchain_event(trustline_request_cancel_event)

    def _generate_trustline_events(self, *, user1, user2, network_address, timestamp):
        events = []
        graph = self.currency_network_graphs[network_address]
        for (from_, to) in [(user1, user2), (user2, user1)]:
            events.append(
                BalanceEvent(
                    network_address,
                    from_,
                    to,
                    graph.get_account_sum(from_, to, timestamp=timestamp),
                    timestamp,
                )
            )
        return events

    def _generate_network_balance_event(self, *, user, network_address, timestamp):
        graph = self.currency_network_graphs[network_address]
        return NetworkBalanceEvent(
            network_address,
            user,
            graph.get_account_sum(user, timestamp=timestamp),
            timestamp,
        )

    def _publish_trustline_events(self, *, user1, user2, network_address, timestamp):
        events = self._generate_trustline_events(
            user1=user1,
            user2=user2,
            network_address=network_address,
            timestamp=timestamp,
        )
        for ev in events:
            self._publish_user_event(ev)

    def _publish_network_balance_event(self, *, user, network_address, timestamp):
        event = self._generate_network_balance_event(
            user=user, network_address=network_address, timestamp=timestamp
        )
        self._publish_user_event(event)

    def _process_trustline_update(self, trustline_update_event):
        logger.debug("Process trustline update event: %s", trustline_update_event)
        self._publish_blockchain_event(trustline_update_event)

    def _publish_blockchain_event(self, event):
        for user in [event.from_, event.to]:
            event_with_user = deepcopy(event)
            event_with_user.user = user
            self._publish_user_event(event_with_user)

    def _publish_user_event(self, event):
        assert event.user is not None
        self.subjects[event.user].publish(event)


def create_engine():
    return sqlalchemy.create_engine(
        URL(
            drivername="postgresql",
            database=os.environ.get("PGDATABASE", ""),
            host=os.environ.get("PGHOST", ""),
            username=os.environ.get("PGUSER", ""),
            password=os.environ.get("PGPASSWORD", ""),
        )
    )
