import logging
import math

import gevent
import socket

from relay.logger import get_logger

logger = get_logger('proxy', logging.DEBUG)


queryBlock = 'latest'
updateBlock = 'pending'

reconnect_interval = 3  # 3s


class Proxy(object):
    event_builders = {}

    def __init__(self, web3, abi, address):
        self._web3 = web3
        self._proxy = web3.eth.contract(abi=abi, address=address)
        self.address = address

    def _watch_filter(self, eventname, function, params=None):
        while True:
            try:
                filter = self._proxy.on(eventname, params)
                filter.watch(function)
                logger.info('Connected to filter for {}:{}'.format(self.address, eventname))
                return filter
            except socket.timeout as err:
                logger.warning('Timeout in filter creation, try to reconnect: ' + str(err))
                gevent.sleep(reconnect_interval)
            except socket.error as err:
                logger.warning('Socketerror in filter creation, try to reconnect:' + str(err))
                gevent.sleep(reconnect_interval)
            except ValueError as err:
                logger.warning('ValueError in filter creation, try to reconnect:' + str(err))
                gevent.sleep(reconnect_interval)

    def start_listen_on(self, eventname, function, params=None):
        def on_exception(filter):
            logger.warning('Filter {} disconnected, trying to reconnect'.format(filter.filter_id))
            gevent.sleep(reconnect_interval)
            filter = self._watch_filter(eventname, function, params)
            filter.link_exception(on_exception)
        if params is None:
            params = {}
        params.setdefault('fromBlock', updateBlock)
        params.setdefault('toBlock', updateBlock)
        filter = self._watch_filter(eventname, function, params)
        filter.link_exception(on_exception)

    def get_events(self, event_name, filter_=None, from_block=0):
        if event_name not in self.event_builders.keys():
            raise ValueError('Unknown eventname {}'.format(event_name))

        if filter_ is None:
            filter_ = {}

        params = {
            'filter': filter_,
            'fromBlock': from_block,
            'toBlock': queryBlock
        }
        list = self._proxy.pastEvents(event_name, params).get(False)
        return sorted_events(self._build_events(list))

    def get_all_events(self, filter_=None, from_block=0):
        all_events = []
        for type in self.event_builders.keys():  # FIXME takes too long.
            # web3.py currently doesn't support getAll() to retrieve all events
            all_events = all_events + self.get_events(type, filter_=filter_, from_block=from_block)
        return sorted_events(all_events)

    def _build_events(self, events):
        current_blocknumber = self._web3.eth.blockNumber

        def build_event(event):
            event_type = event.get('event')
            blocknumber = event.get('blockNumber')
            timestamp = self._web3.eth.getBlock(blocknumber).timestamp
            return self.event_builders[event_type](event, current_blocknumber, timestamp)

        return [build_event(event) for event in events]


def sorted_events(events):
    def key(event):
        if event.blocknumber is None:
            return math.inf
        return event.blocknumber
    return sorted(events, key=key)
