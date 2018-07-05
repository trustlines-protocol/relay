"""provide access to the ethindex database"""

import itertools
import logging
import psycopg2
import psycopg2.extras
from typing import List, Any
from relay.blockchain.currency_network_events import event_builders, from_to_types, CurrencyNetworkEvent
from relay.blockchain.events import BlockchainEvent
import relay.logger
import relay.blockchain.currency_network_proxy
from relay.blockchain.proxy import sorted_events

# proxy.get_all_events just asks for these network events. so we need the list
# here.
standard_event_types = tuple(relay.blockchain.currency_network_proxy.CurrencyNetworkProxy.standard_event_types)

logger = relay.logger.get_logger('ethindex_db', level=logging.DEBUG)


def connect(dsn):
    return psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)


class EventBuilder:
    """Event Builder builds BlockchainEvents from web3 like events We use
    pretty much the same logic like relay.blockchain.Proxy (or it's
    subclasses). The handling for timestamps is different. We also don't ask
    web3 for the currentBlock. It's passed in from the caller.

    So, this could be merged with the implementation in Proxy.
    """

    def __init__(self, _event_builders=None) -> None:
        self.event_builders = _event_builders or event_builders

    def build_events(self, events: List[Any], current_blocknumber: int):
        return [self._build_event(event, current_blocknumber) for event in events]

    def _build_event(
        self, event: Any, current_blocknumber: int
    ) -> BlockchainEvent:
        event_type = event.get("event")  # type: str
        timestamp = event.get("timestamp")  # type: int
        return self.event_builders[event_type](event, current_blocknumber, timestamp)


# we need to 'select * from events' all the time, but we're using lower-case
# identifiers in postgres. The following select statement will give us a
# dictionary with keys in the right case.
select_star_from_events = \
    """SELECT transactionHash "transactionHash",
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


class EthindexDB:
    """EthIndexDB provides a partly compatible interface for the
       relay.blockchain.currency_network_proxy.CurrencyNetworkProxy class

    We implement just enough to make it possible to use this as a drop-in
    replacement for relay.api.resources, that is, just the event reading.

    Since the CurrencyNetworkProxy class operates on one network address only,
    we allow to pass a default network_address in.
    """

    def __init__(self, conn, network_address=None):
        self.conn = conn
        self.default_network_address = network_address
        self.event_builder = EventBuilder(event_builders)

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

    def _get_addr(self, network_address):
        """all the methods here take a network_address argument, which is currently not being used.
        We use the default_network_address instead. Eventually callers will
        need to provide this argument, and we can remove the
        default_network_address. At the least this would be my plan for now.
        """
        r = network_address or self.default_network_address
        assert r, "no network address passed in and no default network address given"
        return r

    def get_network_events(
        self,
        event_name: str,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
        network_address: str = None,
    ) -> List[BlockchainEvent]:
        network_address = self._get_addr(network_address)
        if user_address is None:
            return self.get_events(event_name, from_block=from_block, timeout=timeout, network_address=network_address)
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(
                    select_star_from_events +
                    """WHERE
                          blockNumber>=%s
                          AND eventName=%s
                          AND address=%s
                          AND (args->>'{_from}'=%s or args->>'{_to}'=%s)
                       ORDER BY blocknumber, transactionIndex, logIndex""".format(_from=from_to_types[event_name][0],
                                                                                  _to=from_to_types[event_name][1]),
                    (from_block, event_name, network_address, user_address.lower(), user_address.lower()),
                    # XXX: get rid of .lower calls above when we have checksum addresses
                )
                rows = cur.fetchall()
                events = self._build_events(rows)
        logger.debug("get_network_events(%s, %s, %s, %s) -> %s rows",
                     event_name, from_block, timeout, network_address, len(rows))

        for event in events:
            if isinstance(event, CurrencyNetworkEvent):
                event.user = user_address
            else:
                raise ValueError('Expected a CurrencyNetworkEvent')
        return events

    def get_all_network_events(
        self,
        user_address: str = None,
        from_block: int = 0,
        timeout: float = None,
        network_address: str = None,
    ) -> List[BlockchainEvent]:
        # XXX The following code should be replaced with a proper SQL query.
        # The reason it isn't already a SQL query, is that we need to
        # dynamically create that query.
        results = [self.get_network_events(type, user_address=user_address, from_block=from_block)
                   for type in standard_event_types]
        return sorted_events(list(itertools.chain.from_iterable(results)))

    def get_events(
        self,
        event_name,
        from_block=0,
        timeout: float = None,
        network_address: str = None,
    ) -> List[BlockchainEvent]:
        network_address = self._get_addr(network_address)
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(
                    select_star_from_events +
                    """WHERE
                          blockNumber>=%s
                          AND eventName=%s
                          AND address=%s
                       ORDER BY blocknumber, transactionIndex, logIndex""",
                    (from_block, event_name, network_address),
                )
                rows = cur.fetchall()
                events = self._build_events(rows)
        logger.debug("get_events(%s, %s, %s, %s) -> %s rows",
                     event_name, from_block, timeout, network_address, len(rows))

        return events

    def get_all_events(
        self,
        from_block: int = 0,
        timeout: float = None,
        network_address: str = None,
    ) -> List[BlockchainEvent]:
        network_address = self._get_addr(network_address)
        with self.conn as conn:
            with conn.cursor() as cur:
                cur.execute(
                    select_star_from_events +
                    """WHERE
                          blockNumber>=%s
                          AND address=%s
                          AND eventName in %s
                       ORDER BY blocknumber, transactionIndex, logIndex""",
                    (from_block, network_address, standard_event_types),
                )
                rows = cur.fetchall()
                events = self._build_events(rows)
        logger.debug("get_all_events(%s, %s, %s) -> %s rows",
                     from_block, timeout, network_address, len(rows))

        return events
