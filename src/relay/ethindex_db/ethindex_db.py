"""provide access to the ethindex database"""

import collections
import logging
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
import psycopg2.extras

from relay.blockchain.events import BlockchainEvent, TLNetworkEvent

# proxy.get_all_events just asks for these network events. so we need the list
# here.


logger = logging.getLogger("ethindex_db")


def connect(dsn):
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


def get_latest_ethindex_block_number(conn):
    with conn.cursor() as cur:
        cur.execute("""select * from sync where syncid='default'""")
        row = cur.fetchone()
        if row:
            return row["last_block_number"]
        else:
            raise RuntimeError("Could not determine current block number")


# EventsQuery is used to store a where block together with required parameters
# EthindexDB._run_events_query uses this to build and run a complete query.
EventsQuery = collections.namedtuple("EventsQuery", ["where_block", "params"])


class EventBuilder:
    """Event Builder builds BlockchainEvents from web3 like events We use
    pretty much the same logic like relay.blockchain.Proxy (or its
    subclasses). The handling for timestamps is different. We also don't ask
    web3 for the currentBlock. It's passed in from the caller.
    address_to_contract_types is a mapping from contract_address to type of the contract
    to resolve naming collisions of events when used with different contract types.
    """

    def __init__(
        self,
        _event_builders: Dict[str, Any],
        address_to_contract_types: Dict[str, str] = None,
    ) -> None:
        self.event_builders = _event_builders
        self.address_to_contract_types = address_to_contract_types

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
        if self.address_to_contract_types is not None:
            address: str = event.get("address")
            contract_type = self.address_to_contract_types[address]
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
    """EthIndexDB provides an interface for ethindex database
    it is used to access events from the database.
    """

    def __init__(
        self,
        conn,
        standard_event_types,
        event_builders,
        from_to_types,
        address=None,
        address_to_contract_types: Dict[str, str] = None,
    ):
        self.conn = conn
        self.default_address = address
        self.standard_event_types = standard_event_types
        self.event_builder = EventBuilder(
            event_builders, address_to_contract_types=address_to_contract_types
        )
        self.from_to_types = from_to_types
        self.address_to_contract_types = address_to_contract_types

    @property
    def event_types(self):
        return self.event_builder.event_types

    def _build_events(self, rows):
        return self.event_builder.build_events(rows, self._get_current_blocknumber())

    def _get_current_blocknumber(self):
        return get_latest_ethindex_block_number(self.conn)

    def _get_addr(self, address):
        """all the methods here take an address argument
        At the moment we use the default address instead. Eventually callers will
        need to provide this argument, and we can remove the
        default_address.
        """
        r = address or self.default_address
        assert r, "no contract address passed in and no default contract address given"
        return r

    def _get_standard_event_types(
        self, standard_event_types: Optional[Iterable[str]]
    ) -> Iterable[str]:
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

    def get_user_events(
        self,
        event_type: str,
        user_address: str = None,
        from_block: int = 0,
        contract_address: str = None,
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)
        if user_address is None:
            return self.get_events(
                event_type, from_block=from_block, contract_address=contract_address,
            )
        query = EventsQuery(
            """blockNumber>=%s
               AND eventName=%s
               AND address=%s
               AND (args->>'{_from}'=%s or args->>'{_to}'=%s)
            """.format(
                _from=self.from_to_types[event_type][0],
                _to=self.from_to_types[event_type][1],
            ),
            (from_block, event_type, contract_address, user_address, user_address),
        )

        events = self._run_events_query(query)

        logger.debug(
            "get_user_events(%s, %s, %s, %s) -> %s rows",
            event_type,
            user_address,
            from_block,
            contract_address,
            len(events),
        )

        for event in events:
            if isinstance(event, TLNetworkEvent):
                event.user = user_address
            else:
                raise ValueError("Expected a TLNetworkEvent")
        return events

    def get_all_contract_events(
        self,
        event_types: Iterable[str] = None,
        user_address: str = None,
        from_block: int = 0,
        contract_address: str = None,
    ) -> List[BlockchainEvent]:
        # This function only works properly for many contracts if self.address_to_contract_types is properly set
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
            # We assume self.address_to_contract_types is properly set and not None
            args.append(tuple(self.address_to_contract_types))  # type: ignore

        query = EventsQuery(query_string, args)

        if user_address:
            query = self.add_all_user_types_to_query(query, user_address)

        events = self._run_events_query(query)

        logger.debug(
            "get_all_contract_events(%s, %s, %s, %s) -> %s rows",
            event_types,
            user_address,
            from_block,
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
        self, event_type, from_block: int = 0, contract_address: str = None
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)
        query = EventsQuery(
            """blockNumber>=%s
               AND eventName=%s
               AND address=%s""",
            (from_block, event_type, contract_address),
        )
        events = self._run_events_query(query)

        logger.debug(
            "get_events(%s, %s, %s) -> %s rows",
            event_type,
            from_block,
            contract_address,
            len(events),
        )

        return events

    def get_events_from_to(
        self,
        event_types: Iterable[str] = None,
        start_time: int = 0,
        end_time: int = None,
        contract_address: str = None,
        from_address: str = None,
        to_address: str = None,
    ):
        """
        Get events with given parameters.

        If `from_address` and `to_address` are set, will find all events with matching `from` and `to` for given event
        types. e.g. for a TrustlineUpdate it will match for `_creditor` and `_debtor`.

        If no event_types is given, uses self.standard_event_types.
        """
        if event_types is None:
            event_types = self.standard_event_types

        query_strings = []
        query_params: List[Any] = []

        if from_address is not None or to_address is not None:
            from_to_string, from_to_args = self.get_query_for_from_to(
                event_types, from_address, to_address
            )
            query_strings.append(from_to_string)
            query_params += from_to_args
        elif event_types is not None:
            query_strings.append("eventName in %s")
            query_params.append(tuple(event_types))

        if start_time != 0:
            query_strings.append("timestamp>=%s")
            query_params.append(start_time)
        if end_time is not None:
            query_strings.append("timestamp<=%s")
            query_params.append(end_time)

        contract_address = self._get_addr(contract_address)
        query_strings.append("address=%s")
        query_params.append(contract_address)

        query = EventsQuery(" AND ".join(query_strings), query_params)

        events = self._run_events_query(query)

        logger.debug(
            "get_events_from_to(%s, %s, %s, %s, %s, %s) -> %s rows",
            event_types,
            start_time,
            end_time,
            contract_address,
            from_address,
            to_address,
            len(events),
        )

        return events

    def get_query_for_from_to(self, event_types, from_address, to_address):
        """
        Make a query string for finding events of types `event_types` with matching `from_address` and `to_address`

        Assumes self.from_to_types is properly set for given event_types
        """

        if from_address is None and to_address is None:
            raise ValueError(
                "Cannot filter for from_address and to_address if addresses are None"
            )

        event_type_from_to_query_strings = []
        query_params = []

        for event_type in event_types:
            if event_type not in self.from_to_types.keys():
                raise ValueError(
                    f"No `from_to_types` for given event type: {event_type}"
                )
            query_params.append(event_type)
            user_types = self.from_to_types[event_type]

            from_string = ""
            to_string = ""
            if from_address is not None:
                from_string = f"args->>'{user_types[0]}'=%s"
                query_params.append(from_address)
            if to_address is not None:
                to_string = f"args->>'{user_types[1]}'=%s"
                query_params.append(to_address)

            coordinator = ""
            if from_string != "" and to_string != "":
                coordinator = " AND "
            from_to_query_string = from_string + coordinator + to_string

            event_type_from_to_string = (
                "(eventName=%s AND (" + from_to_query_string + "))"
            )

            event_type_from_to_query_strings.append(event_type_from_to_string)

        final_string = " OR ".join(
            string for string in event_type_from_to_query_strings
        )

        return final_string, query_params

    def get_all_events(
        self,
        from_block: int = 0,
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
            "get_all_events(%s, %s, standard_event_types) -> %s rows",
            from_block,
            contract_address,
            len(events),
        )

        return events

    def get_transaction_events(
        self, tx_hash: str, from_block: int = 0, event_types: Iterable = None
    ):
        event_types = self._get_standard_event_types(event_types)

        query = EventsQuery(
            """blockNumber>=%s
               AND transactionHash=%s
               AND eventName in %s
            """,
            (from_block, tx_hash, tuple(event_types)),
        )

        events = self._run_events_query(query)

        logger.debug(
            "get_transaction_events(%s, %s, %s) -> %s rows",
            tx_hash,
            from_block,
            event_types,
            len(events),
        )

        return events

    def get_transaction_events_by_event_id(
        self, block_hash, log_index, event_types: Iterable = None
    ):
        """Gets all events from a transaction
        where event_id is the id of one of the events within the transaction"""

        event_types = self._get_standard_event_types(event_types)

        query = EventsQuery(
            """blockHash=%s
            AND eventName in %s
            AND transactionHash IN
                (SELECT transactionHash "transactionHash" FROM events WHERE blockHash=%s AND logIndex=%s LIMIT 1)
            """,
            (block_hash, tuple(event_types), block_hash, log_index),
        )

        transaction_events = self._run_events_query(query)

        logger.debug(
            "get_transaction_events_by_event_id(%s, %s, %s) -> %s rows",
            block_hash,
            log_index,
            event_types,
            len(transaction_events),
        )

        return transaction_events

    def add_all_user_types_to_query(self, events_query: EventsQuery, user_address: str):
        all_user_types = set()
        for user_types in self.from_to_types.values():
            for user_type in user_types:
                all_user_types.add(user_type)
        user_where = " or ".join(
            f"args->>'{user_type}'=%s" for user_type in all_user_types
        )
        query_string = events_query.where_block + f"AND ({user_where})"
        args = events_query.params
        for _ in range(len(all_user_types)):
            args.append(user_address)

        return EventsQuery(query_string, args)


class CurrencyNetworkEthindexDB(EthindexDB):
    def get_network_events(
        self, event_type: str, user_address: str = None, from_block: int = 0,
    ) -> List[BlockchainEvent]:
        return self.get_user_events(event_type, user_address, from_block)

    def get_all_network_events(
        self,
        user_address: str = None,
        from_block: int = 0,
        event_types: Iterable[str] = None,
    ) -> List[BlockchainEvent]:
        if self.default_address is None:
            # if the default address is not set we will get events from non currency network contracts
            raise RuntimeError(
                "Cannot get all network events if CurrencyNetworkEthindexDB address is not set."
            )
        return self.get_all_contract_events(
            event_types=event_types, user_address=user_address, from_block=from_block,
        )

    def get_trustline_events(
        self,
        contract_address: str,
        user_address: str,
        counterparty_address: str,
        event_types: Iterable[str] = None,
        from_block: int = 0,
    ):
        event_types = self._get_standard_event_types(event_types)

        all_event_fieldname_combination = set()
        for from_, to in self.from_to_types.values():
            all_event_fieldname_combination.add((from_, to))
            all_event_fieldname_combination.add((to, from_))

        member_filter_block = " OR ".join(
            f"(args->>'{field_a}'=%s AND args->>'{field_b}'=%s)"
            for field_a, field_b in all_event_fieldname_combination
        )

        args: List[Any] = [from_block, tuple(event_types), contract_address]
        for _ in all_event_fieldname_combination:
            args.extend((user_address, counterparty_address))

        query = EventsQuery(
            f"""blockNumber>=%s
               AND eventName in %s
               AND address=%s
               AND ({member_filter_block})
            """,
            args,
        )

        events = self._run_events_query(query)

        logger.debug(
            "get_trustline_events(%s, %s, %s, %s, %s) -> %s rows",
            contract_address,
            user_address,
            counterparty_address,
            event_types,
            from_block,
            len(events),
        )

        for event in events:
            if isinstance(event, TLNetworkEvent):
                event.user = user_address
            else:
                raise ValueError("Expected a TLNetworkEvent")
        return events


class ExchangeEthindexDB(EthindexDB):
    def get_all_exchange_events_of_user(
        self,
        user_address: str,
        all_exchange_addresses: Iterable[str],
        type: str,
        from_block: int,
    ):

        event_types = self._get_standard_event_types([type])

        query_string = """blockNumber>=%s
                            AND eventName in %s
                            AND address in %S"""
        args = [from_block, event_types, all_exchange_addresses]
        events_query = EventsQuery(query_string, args)
        events_query = self.add_all_user_types_to_query(events_query, user_address)

        events = self._run_events_query(events_query)

        logger.debug(
            "get_all_exchange_events_of_user(%s, %s, %s, %s) -> %s rows",
            user_address,
            all_exchange_addresses,
            type,
            from_block,
            len(events),
        )

        return events
