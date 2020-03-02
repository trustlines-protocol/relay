"""provide access to the ethindex database"""

import collections
import logging
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras

from relay.blockchain import (
    currency_network_events,
    exchange_events,
    token_events,
    unw_eth_events,
)
from relay.blockchain.events import BlockchainEvent, TLNetworkEvent

# proxy.get_all_events just asks for these network events. so we need the list
# here.


logger = logging.getLogger("ethindex_db")


def connect(dsn):
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


# EventsQuery is used to store a where block together with required parameters
# EthindexDB._run_events_query uses this to build and run a complete query.
EventsQuery = collections.namedtuple("EventsQuery", ["where_block", "params"])


class EventBuilder:
    """Event Builder builds BlockchainEvents from web3 like events We use
    pretty much the same logic like relay.blockchain.Proxy (or its
    subclasses). The handling for timestamps is different. We also don't ask
    web3 for the currentBlock. It's passed in from the caller.
    contract_types is a mapping from contract_address to type of the contract
    to resolve naming collisions of events when used with different contract types.
    """

    def __init__(
        self, _event_builders: Dict[str, Any], contract_types: Dict[str, str] = None
    ) -> None:
        self.event_builders = _event_builders
        self.contract_types = contract_types

    def build_events(
        self, events: List[Any], current_blocknumber: int
    ) -> List[BlockchainEvent]:
        return [self._build_event(event, current_blocknumber) for event in events]

    @property
    def event_types(self) -> List[str]:
        return list(self.event_builders.keys())

    def _build_event(self, event: Any, current_blocknumber: int) -> BlockchainEvent:
        event_type: str = event.get("event")
        timestamp: int = event.get("timestamp")
        if self.contract_types is not None:
            address: str = event.get("address")
            contract_type = self.contract_types[address]
        else:
            contract_type = ""
        return self.event_builders[contract_type + event_type](
            event, current_blocknumber, timestamp
        )


# we need to 'select * from events' all the time, but we're using lower-case
# identifiers in postgres. The following select statement will give us a
# dictionary with keys in the right case.
select_star_from_events = """SELECT transactionHash "transactionHash",
              blockNumber "blockNumber",
              address,
              eventName "event",
              args,
              blockHash "blockHash",
              transactionIndex "transactionIndex",
              logIndex "logIndex",
              timestamp
       FROM events
    """

order_by_default_sort_order = """ ORDER BY blocknumber, transactionIndex, logIndex
    """


class EthindexDB:
    """EthIndexDB provides a partly compatible interface for the
       relay.blockchain.currency_network_proxy.CurrencyNetworkProxy,
       relay.blockchain.token_proxy.TokenProxy and
       relay.blockchain.unw_eth_proxy.UnwEthProxy classes

    We implement just enough to make it possible to use this as a drop-in
    replacement for relay.api.resources, that is, just the event reading.

    Since the proxy classes operates on one network address only,
    we allow to pass a default address in.
    """

    def __init__(
        self,
        conn,
        standard_event_types,
        event_builders,
        from_to_types,
        address=None,
        contract_types=None,
    ):
        self.conn = conn
        self.default_address = address
        self.standard_event_types = standard_event_types
        self.event_builder = EventBuilder(event_builders, contract_types=contract_types)
        self.from_to_types = from_to_types
        self.contract_types = contract_types

    @property
    def event_types(self):
        return self.event_builder.event_types

    def _build_events(self, rows):
        return self.event_builder.build_events(rows, self._get_current_blocknumber())

    def _get_current_blocknumber(self):
        with self.conn.cursor() as cur:
            cur.execute("""select * from sync where syncid='default'""")
            row = cur.fetchone()
            if row:
                return row["last_block_number"]
            else:
                raise RuntimeError("Could not determine current block number")

    def _get_addr(self, address):
        """all the methods here take an address argument
        At the moment we use the default address instead. Eventually callers will
        need to provide this argument, and we can remove the
        default_address.
        """
        r = address or self.default_address
        assert r, "no network address passed in and no default network address given"
        return r

    def _get_standard_event_types(self, standard_event_types):
        r = standard_event_types or self.standard_event_types
        assert r, "no standard event passed in and no default events given"
        return r

    def _run_events_query(self, events_query: EventsQuery) -> List[BlockchainEvent]:
        """run a query on the events table"""
        query_string = "{select_star_from_events} WHERE {where_block} {order_by_default_sort_order}".format(
            select_star_from_events=select_star_from_events,
            where_block=events_query.where_block,
            order_by_default_sort_order=order_by_default_sort_order,
        )

        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(query_string, events_query.params)
                rows = cur.fetchall()
                return self._build_events(rows)

    def get_network_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
    ) -> List[BlockchainEvent]:
        """Function for compatibility with relay.blockchain.CurrencyNetworkProxy.
        Will be removed after a refactoring
        """
        return self.get_user_events(event_name, user_address, from_block, timeout)

    def get_unw_eth_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
    ) -> List[BlockchainEvent]:
        """Function for compatibility with relay.blockchain.UnwEthProxy. Will be removed after a refactoring"""
        return self.get_user_events(event_name, user_address, from_block, timeout)

    def get_token_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
    ) -> List[BlockchainEvent]:
        """Function for compatibility with relay.blockchain.TokenProxy. Will be removed after a refactoring"""
        return self.get_user_events(event_name, user_address, from_block, timeout)

    def get_exchange_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
    ) -> List[BlockchainEvent]:
        """Function for compatibility with relay.blockchain.ExchangeProxy. Will be removed after a refactoring"""
        return self.get_user_events(event_name, user_address, from_block, timeout)

    def get_user_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
        contract_address: str = None,
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)
        if user_address is None:
            return self.get_events(
                event_name,
                from_block=from_block,
                timeout=timeout,
                contract_address=contract_address,
            )
        query = EventsQuery(
            """blockNumber>=%s
               AND eventName=%s
               AND address=%s
               AND (args->>'{_from}'=%s or args->>'{_to}'=%s)
            """.format(
                _from=self.from_to_types[event_name][0],
                _to=self.from_to_types[event_name][1],
            ),
            (from_block, event_name, contract_address, user_address, user_address),
        )

        events = self._run_events_query(query)

        logger.debug(
            "get_user_events(%s, %s, %s, %s, %s) -> %s rows",
            event_name,
            user_address,
            from_block,
            timeout,
            contract_address,
            len(events),
        )

        for event in events:
            if isinstance(event, TLNetworkEvent):
                event.user = user_address
            else:
                raise ValueError("Expected a TLNetworkEvent")
        return events

    def get_trustline_events(
        self,
        contract_address: str,
        user_address: str,
        counterparty_address: str,
        event_name: str = None,
        from_block: int = 0,
        timeout: float = None,
    ):
        if event_name is None:
            query = EventsQuery(
                """blockNumber>=%s
                   AND address=%s
                   AND ((args->>'{_from}'=%s AND args->>'{_to}'=%s) OR (args->>'{_from}'=%s AND args->>'{_to}'=%s))
                """.format(
                    _from=self.from_to_types[event_name][0],
                    _to=self.from_to_types[event_name][1],
                ),
                (
                    from_block,
                    event_name,
                    contract_address,
                    user_address,
                    counterparty_address,
                    counterparty_address,
                    user_address,
                ),
            )
        else:
            query = EventsQuery(
                """blockNumber>=%s
                   AND eventName=%s
                   AND address=%s
                   AND ((args->>'{_from}'=%s AND args->>'{_to}'=%s) OR (args->>'{_from}'=%s AND args->>'{_to}'=%s))
                """.format(
                    _from=self.from_to_types[event_name][0],
                    _to=self.from_to_types[event_name][1],
                ),
                (
                    from_block,
                    event_name,
                    contract_address,
                    user_address,
                    counterparty_address,
                    counterparty_address,
                    user_address,
                ),
            )

        events = self._run_events_query(query)

        logger.debug(
            "get_trustline_events(%s, %s, %s, %s, %s, %s) -> %s rows",
            contract_address,
            user_address,
            counterparty_address,
            event_name,
            from_block,
            timeout,
            len(events),
        )

        for event in events:
            if isinstance(event, TLNetworkEvent):
                event.user = user_address
            else:
                raise ValueError("Expected a TLNetworkEvent")
        return events

    def get_all_unw_eth_events(
        self, user_address: str = None, from_block: int = 0, timeout: float = None
    ) -> List[BlockchainEvent]:
        return self.get_all_contract_events(
            unw_eth_events.standard_event_types, user_address, from_block, timeout
        )

    def get_all_token_events(
        self, user_address: str = None, from_block: int = 0, timeout: float = None
    ) -> List[BlockchainEvent]:
        return self.get_all_contract_events(
            token_events.standard_event_types, user_address, from_block, timeout
        )

    def get_all_network_events(
        self, user_address: str = None, from_block: int = 0, timeout: float = None
    ) -> List[BlockchainEvent]:
        return self.get_all_contract_events(
            currency_network_events.standard_event_types,
            user_address,
            from_block,
            timeout,
        )

    def get_all_exchange_events(
        self, user_address: str = None, from_block: int = 0, timeout: float = None
    ) -> List[BlockchainEvent]:
        return self.get_all_contract_events(
            exchange_events.standard_event_types, user_address, from_block, timeout
        )

    def get_all_contract_events(
        self,
        event_types: List[str] = None,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
        contract_address: str = None,
    ) -> List[BlockchainEvent]:
        # This function only works properly for many contracts if self.contract_types is properly set
        # TODO Refactor and move somewhere else
        contract_address = contract_address or self.default_address

        event_types = self._get_standard_event_types(event_types)
        query_string = "blockNumber>=%s "
        args: List[Any] = [from_block]

        if event_types:
            query_string += "AND eventName in %s "
            args.append(tuple(event_types))

        if contract_address:
            query_string += "AND address=%s "
            args.append(contract_address)
        else:
            query_string += "AND address in %s "
            args.append(tuple(self.contract_types))

        if user_address:
            all_user_types = set()
            for user_types in self.from_to_types.values():
                for user_type in user_types:
                    all_user_types.add(user_type)
            user_where = " or ".join(
                f"args->>'{user_type}'=%s" for user_type in all_user_types
            )
            query_string += f"AND ({user_where})"
            for _ in range(len(all_user_types)):
                args.append(user_address)

        query = EventsQuery(query_string, args)

        events = self._run_events_query(query)

        logger.debug(
            "get_all_contract_events(%s, %s, %s, %s, %s) -> %s rows",
            event_types,
            user_address,
            from_block,
            timeout,
            contract_address,
            len(events),
        )

        for event in events:
            if isinstance(event, TLNetworkEvent):
                event.user = user_address
            else:
                raise ValueError("Expected a TLNetworkEvent")
        return events

    def get_events(
        self,
        event_name,
        from_block=0,
        timeout: float = None,
        contract_address: str = None,
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)
        query = EventsQuery(
            """blockNumber>=%s
               AND eventName=%s
               AND address=%s""",
            (from_block, event_name, contract_address),
        )
        events = self._run_events_query(query)

        logger.debug(
            "get_events(%s, %s, %s, %s) -> %s rows",
            event_name,
            from_block,
            timeout,
            contract_address,
            len(events),
        )

        return events

    def get_all_events(
        self,
        from_block: int = 0,
        timeout: float = None,
        contract_address: str = None,
        standard_event_types=None,
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)
        standard_event_types = self._get_standard_event_types(standard_event_types)
        query = EventsQuery(
            """blockNumber>=%s
               AND address=%s
               AND eventName in %s""",
            (from_block, contract_address, tuple(standard_event_types)),
        )

        events = self._run_events_query(query)
        logger.debug(
            "get_all_events(%s, %s, %s) -> %s rows",
            from_block,
            timeout,
            contract_address,
            len(events),
        )

        return events
