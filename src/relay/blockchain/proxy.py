import functools
import itertools
import logging
import math
import socket
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Mapping, Optional, Set

import eth_utils
import gevent
import hexbytes
from gevent import Greenlet
from gevent.queue import Queue
from web3._utils.events import get_event_data

import relay.concurrency_utils as concurrency_utils

from .events import BlockchainEvent

logger = logging.getLogger("proxy")


queryBlock = "latest"
updateBlock = "pending"

reconnect_interval = 3  # 3s


def get_new_entries(filter, callback):
    new_entries = filter.get_new_entries()
    if new_entries:
        logger.debug("new entries for filter %s: %s", filter, new_entries)
    for event in new_entries:
        callback(event)


def watch_filter(filter, callback):
    while True:
        get_new_entries(filter, callback)
        gevent.sleep(1.0)


class LogFilterListener:
    """Listens for new logs for several contract proxies and notifies them"""

    def __init__(self, web3, filter_params: Dict[str, Any] = None):
        self._web3 = web3
        self._proxies: Dict[str, Proxy] = {}
        self._watch_filter_greenlet = None
        self.currently_watched_addresses: Set[str] = set()
        self._filter_params = filter_params
        if self._filter_params is None:
            self._filter_params = {}

    def add_proxy(self, proxy: "Proxy"):
        """Add a new proxy to listen for logs"""
        self._proxies[proxy.address] = proxy

    def start(self):
        """Start or restart listening for logs for the currently registered proxies"""
        proxy_addresses = set(self._proxies.keys())
        if (
            self._watch_filter_greenlet is not None
            and proxy_addresses == self.currently_watched_addresses
        ):
            # Nothing to do, everything is running
            return

        if self._watch_filter_greenlet is not None:
            self._watch_filter_greenlet.kill()

        self._filter_params.setdefault("fromBlock", updateBlock)
        self._filter_params.setdefault("toBlock", updateBlock)
        self._filter_params["address"] = list(proxy_addresses)

        self._watch_filter_greenlet = self._watch_filter(
            self._process_log, self._filter_params
        )
        self.currently_watched_addresses = proxy_addresses

        def on_exception(greenlet):
            logger.warning(
                "Filter {} disconnected, trying to reconnect".format(greenlet)
            )
            try:
                greenlet.get()
            except Exception as e:
                logger.warning(f"Reason: {e}")
            gevent.sleep(reconnect_interval)
            greenlet = self._watch_filter(self._process_log, self._filter_params)
            greenlet.link_exception(on_exception)

        self._watch_filter_greenlet.link_exception(on_exception)
        return self

    def stop(self):
        if self._watch_filter_greenlet is not None:
            self._watch_filter_greenlet.kill()
            self._watch_filter_greenlet = None

    def _watch_filter(self, function: Callable, params: Dict):
        while True:
            try:
                filter = self._web3.eth.filter(params)
                watch_filter_greenlet = gevent.spawn(watch_filter, filter, function)
                logger.info("Connected to filter for {}".format(params["address"]))
                return watch_filter_greenlet
            except socket.timeout as err:
                logger.warning(
                    "Timeout in filter creation, try to reconnect: " + str(err)
                )
                gevent.sleep(reconnect_interval)
            except socket.error as err:
                logger.warning(
                    "Socketerror in filter creation, try to reconnect:" + str(err)
                )
                gevent.sleep(reconnect_interval)
            except ValueError as err:
                logger.warning(
                    "ValueError in filter creation, try to reconnect:" + str(err)
                )
                gevent.sleep(reconnect_interval)

    def _process_log(self, log) -> None:
        self._proxies[log["address"]]._register_raw_event_log(log)


class Proxy(object):
    event_builders: Mapping[str, Callable[[Any, int, int], BlockchainEvent]] = {}
    standard_event_types: List[str] = []

    def __init__(self, web3, abi, address: str) -> None:
        self._web3 = web3
        self._proxy = web3.eth.contract(abi=abi, address=address)
        self.address = address
        self._event2log_queue: Dict[str, Queue] = defaultdict(Queue)
        self._topic2event_abi = {
            hexbytes.HexBytes(eth_utils.event_abi_to_log_topic(event_abi)): event_abi
            for event_abi in self._proxy.events._events
        }
        self._log_listener: Optional[LogFilterListener] = None

    def start_listen_on(
        self, eventname: str, function: Callable, *, start_log_filter=True
    ) -> Greenlet:
        """
        Starts listening for new events with name `eventname` and call the function for every received event
        if start_log_filter is true, also start a log filter to listen for the logs.
        """
        self._event2log_queue[eventname] = Queue()

        def poll_from_queue():
            try:
                for event in self._event2log_queue[eventname]:
                    function(event)
            except Greenlet.GreenletExit:
                logger.info("Received kill, shutting down")
                if self._log_listener is not None:
                    self._log_listener.stop()
                    self._log_listener = None

        if start_log_filter and self._log_listener is None:
            self._log_listener = LogFilterListener(self._web3)
            self._log_listener.add_proxy(self)
            self._log_listener.start()
        watch_filter_greenlet = gevent.spawn(poll_from_queue)
        return watch_filter_greenlet

    def get_events(
        self, event_name, filter_=None, from_block=0, timeout: float = None
    ) -> List[BlockchainEvent]:
        if event_name not in self.event_builders.keys():
            raise ValueError("Unknown eventname {}".format(event_name))

        if filter_ is None:
            filter_ = {}

        logfilter = getattr(self._proxy.events, event_name).createFilter(
            fromBlock=from_block, toBlock=queryBlock, argument_filters=filter_
        )

        queries = [logfilter.get_all_entries]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(self._build_events(results[0]))

    def get_all_events(
        self, filter_=None, from_block: int = 0, timeout: float = None
    ) -> List[BlockchainEvent]:
        queries = [
            functools.partial(
                self.get_events, type, filter_=filter_, from_block=from_block
            )
            for type in self.standard_event_types
        ]
        results = concurrency_utils.joinall(queries, timeout=timeout)
        return sorted_events(list(itertools.chain.from_iterable(results)))

    def _build_events(self, events: List[Any]):
        current_blocknumber = self._web3.eth.blockNumber
        return [self._build_event(event, current_blocknumber) for event in events]

    def _register_raw_event_log(self, raw_event_log) -> None:
        """Registers a new log to be decoded and sent to the correct event listener"""
        event = get_event_data(self._get_abi_for_log(raw_event_log), raw_event_log)
        self._event2log_queue[event.event].put(event)

    def _get_abi_for_log(self, raw_event_log):
        topic = hexbytes.HexBytes(raw_event_log["topics"][0])
        event_abi = self._topic2event_abi.get(topic)
        if event_abi is None:
            raise RuntimeError(
                f"Could not find event abi for log {raw_event_log} on contract {self.address}. "
                "{topic} not in {self._topic2event_abi.keys()}"
            )
        return event_abi

    def _build_event(
        self, event: Any, current_blocknumber: int = None
    ) -> BlockchainEvent:
        event_type: str = event.get("event")
        blocknumber: int = event.get("blockNumber")
        if current_blocknumber is None:
            current_blocknumber = blocknumber
        timestamp: int = self._get_block_timestamp(blocknumber)
        return self.event_builders[event_type](event, current_blocknumber, timestamp)

    def _get_block_timestamp(self, blocknumber: int) -> int:
        if blocknumber is not None:
            timestamp = self._web3.eth.getBlock(blocknumber).timestamp
        else:
            timestamp = time.time()
        return timestamp


def sorted_events(events: List[BlockchainEvent]) -> List[BlockchainEvent]:
    def key(event):
        if event.blocknumber is None:
            return math.inf
        return event.blocknumber

    return sorted(events, key=key)
