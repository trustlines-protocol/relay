"""provide access to the ethindex database"""

import logging
from typing import Any, Dict, Iterable, List, Optional

import psycopg2
import psycopg2.extras

from relay.blockchain import currency_network_events
from relay.blockchain.currency_network_events import (
    DebtUpdateEvent,
    DebtUpdateEventType,
)
from relay.blockchain.events import BlockchainEvent, TLNetworkEvent

logger = logging.getLogger("ethindex_db")


def connect(dsn):
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


# we need to 'select * from events' all the time, but we're using lower-case
# identifiers in postgres. The following select statement will give us a
# dictionary with keys in the right case.
select_star_from_events = """
    SELECT
        transactionHash "transactionHash",
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

order_by_default_sort_order = """ORDER BY blocknumber, transactionIndex, logIndex"""


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


class EthindexDB:
    """EthIndexDB provides an interface for ethindex database
    it used to access events from the database.
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

    def _get_standard_event_types(
        self, standard_event_types: Optional[Iterable[str]]
    ) -> Iterable[str]:
        r = standard_event_types or self.standard_event_types
        assert r, "no standard event passed in and no default events given"
        return r

    def _format_query_string(
        self,
        where_block,
        select_block=select_star_from_events,
        order_by_block=order_by_default_sort_order,
        limit_block="",
    ):
        """Format a query string with given inputs"""
        return f"{select_block} {where_block} {order_by_block} {limit_block}"

    def _run_query_where_block(self, where_block, query_params):
        """Run a query formatted with where_block and params"""
        if not where_block.startswith("WHERE"):
            raise ValueError("where_block must start with WHERE")
        query_string = self._format_query_string(where_block)
        return self._run_events_query(query_string, query_params)

    def _run_events_query(
        self, query_string: str, query_params: Iterable
    ) -> List[BlockchainEvent]:
        """run a query on the events table"""
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(query_string, query_params)
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

        where_block = """WHERE blockNumber>=%s
               AND eventName=%s
               AND address=%s
               AND (args->>'{_from}'=%s or args->>'{_to}'=%s)
            """.format(
            _from=self.from_to_types[event_type][0],
            _to=self.from_to_types[event_type][1],
        )
        query_params = (
            from_block,
            event_type,
            contract_address,
            user_address,
            user_address,
        )
        events = self._run_query_where_block(where_block, query_params)

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
        # This function only works properly for many contracts if self.contract_types is properly set
        # TODO Refactor and move somewhere else
        contract_address = contract_address or self.default_address

        event_types = self._get_standard_event_types(event_types)
        where_block = "WHERE blockNumber>=%s "
        args: List[Any] = [from_block]

        if event_types:
            where_block += "AND eventName in %s "
            args.append(tuple(event_types))

        if contract_address:
            where_block += "AND address=%s "
            args.append(contract_address)
        else:
            where_block += "AND address in %s "
            args.append(tuple(self.contract_types))

        if user_address:
            all_user_types = set()
            for user_types in self.from_to_types.values():
                for user_type in user_types:
                    all_user_types.add(user_type)
            user_where = " or ".join(
                f"args->>'{user_type}'=%s" for user_type in all_user_types
            )
            where_block += f"AND ({user_where})"
            for _ in range(len(all_user_types)):
                args.append(user_address)

        events = self._run_query_where_block(where_block, args)

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
        self, event_type, from_block=0, contract_address: str = None,
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)

        where_block = """WHERE
            blockNumber>=%s
            AND eventName=%s
            AND address=%s"""
        query_params = (from_block, event_type, contract_address)

        events = self._run_query_where_block(where_block, query_params)

        logger.debug(
            "get_events(%s, %s, %s) -> %s rows",
            event_type,
            from_block,
            contract_address,
            len(events),
        )

        return events

    def get_all_events(
        self,
        from_block: int = 0,
        contract_address: str = None,
        standard_event_types=None,
    ) -> List[BlockchainEvent]:
        contract_address = self._get_addr(contract_address)
        standard_event_types = self._get_standard_event_types(standard_event_types)

        where_block = """WHERE blockNumber>=%s
            AND address=%s
            AND eventName in %s"""
        query_params = (from_block, contract_address, tuple(standard_event_types))

        events = self._run_query_where_block(where_block, query_params)

        logger.debug(
            "get_all_events(%s, %s, %s) -> %s rows",
            from_block,
            contract_address,
            len(events),
        )

        return events

    def get_transaction_events(
        self, tx_hash: str, from_block: int = 0, event_types: Iterable = None
    ):
        event_types = self._get_standard_event_types(event_types)

        where_block = """WHERE blockNumber>=%s
               AND transactionHash=%s
               AND eventName in %s
            """
        query_params = (from_block, tx_hash, tuple(event_types))

        events = self._run_query_where_block(where_block, query_params)
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

        where_block = f"""WHERE blockHash=%s
            AND eventName in %s
            AND transactionHash IN
                (SELECT transactionHash "transactionHash" FROM events WHERE blockHash=%s AND logIndex=%s LIMIT 1)
            """
        query_params = (block_hash, tuple(event_types), block_hash, log_index)

        transaction_events = self._run_query_where_block(where_block, query_params)

        logger.debug(
            "get_transaction_events_by_event_id(%s, %s, %s) -> %s rows",
            block_hash,
            log_index,
            event_types,
            len(transaction_events),
        )

        return transaction_events


class CurrencyNetworkEthindexDB(EthindexDB):
    def get_network_events(
        self, event_type: str, user_address: str = None, from_block: int = 0,
    ) -> List[BlockchainEvent]:
        return self.get_user_events(event_type, user_address, from_block)

    def get_all_network_events(
        self, user_address: str = None, from_block: int = 0
    ) -> List[BlockchainEvent]:
        return self.get_all_contract_events(
            currency_network_events.standard_event_types, user_address, from_block,
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

        where_block = f"""WHERE blockNumber>=%s
               AND eventName in %s
               AND address=%s
               AND ({member_filter_block})
            """
        events = self._run_query_where_block(where_block, args)

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

    def get_last_two_debt_update_events(self, tx_hash) -> List[DebtUpdateEvent]:
        # TODO: this is not reliable if there is more than one DebtUpdate event in the transaction

        from_type = self.from_to_types[DebtUpdateEventType][0]
        to_type = self.from_to_types[DebtUpdateEventType][1]

        # We want DebtUpdate events where `from` and `to` are in (`a`, `b`)
        # where `a` and `b` are the `from` and `two` of the DebtUpdate of the matched transactionHash.
        # We want the last two of these events that occurred before the event in tx_hash
        query_string = f"""
            WITH transaction_debt_update AS (
                SELECT args, blockNumber, logIndex FROM events WHERE eventName=%s AND transactionHash=%s LIMIT 1
            )

            {select_star_from_events} WHERE
                eventName=%s
                AND (args->>'{from_type}', args->>'{to_type}')
                    IN (SELECT args->>'{from_type}', args->>'{to_type}' FROM transaction_debt_update)
                AND blockNumber <= (SELECT blockNumber FROM transaction_debt_update)
                AND logIndex <= (SELECT logIndex FROM transaction_debt_update)

            ORDER BY blockNumber, transactionIndex, logIndex DESC
            LIMIT 2
        """
        query_params = (DebtUpdateEventType, tx_hash, DebtUpdateEventType)

        # We know from the query that the type of events is DebtUpdateEvent
        events: List[DebtUpdateEvent] = self._run_events_query(query_string, query_params)  # type: ignore

        logger.debug(
            "get_last_two_debt_update_events(%s) -> %s rows", tx_hash, len(events),
        )

        return events
