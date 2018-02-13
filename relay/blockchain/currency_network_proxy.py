import logging
import socket
from collections import namedtuple

import gevent

from .proxy import Proxy, reconnect_interval
from relay.logger import get_logger


class Trustline(namedtuple('Trustline',
                           ['address', 'creditline_ab', 'creditline_ba', 'interest_ab', 'interest_ba',
                            'fees_outstanding_a', 'fees_outstanding_b', 'm_time', 'balance_ab'])):
    __slots__ = ()

    def __new__(cls, address, creditline_ab=0, creditline_ba=0, interest_ab=0, interest_ba=0, fees_outstanding_a=0,
                fees_outstanding_b=0, m_time=0, balance_ab=0):
        return super(Trustline, cls).__new__(cls, address, creditline_ab, creditline_ba, interest_ab, interest_ba,
                                             fees_outstanding_a, fees_outstanding_b, m_time, balance_ab)


logger = get_logger('currency network', logging.DEBUG)


# Constants
CreditlineRequestEvent = 'CreditlineUpdateRequest'
CreditlineUpdatedEvent = 'CreditlineUpdate'
BalanceUpdatedEvent = 'BalanceUpdate'
TransferEvent = 'Transfer'
PathPreparedEvent = 'PathPrepared'
ChequeCashed = 'ChequeCashed'


class CurrencyNetworkProxy(Proxy):
    event_types = [TransferEvent, CreditlineRequestEvent, CreditlineUpdatedEvent]

    def __init__(self, web3, abi, address):
        super().__init__(web3, abi, address)

    @property
    def name(self):
        return self._proxy.call().name().strip('\0')

    @property
    def decimals(self):
        return self._proxy.call().decimals()

    @property
    def symbol(self):
        return self._proxy.call().symbol().strip('\0')

    @property
    def users(self):
        return list(self._proxy.call().getUsers())

    def friends(self, user_address):
        return list(self._proxy.call().getFriends(user_address))

    def account(self, a_address, b_address):
        return self._proxy.call().getAccount(a_address, b_address)

    def spendable(self, a_address):
        return self._proxy.call().spendable(a_address)

    def spendableTo(self, a_address, b_address):
        return self._proxy.call().spendableTo(a_address, b_address)

    def gen_graph_representation(self):
        """Returns the trustlines network as a dict address -> list of Friendships"""
        result = {}
        for user in self.users:
            list = []
            for friend in self.friends(user):
                if user < friend:
                    (creditline_ab,
                     creditline_ba,
                     interest_ab,
                     interest_ba,
                     fees_outstanding_a,
                     fees_outstanding_b,
                     mtime,
                     balance_ab) = self.account(user, friend)
                    list.append(Trustline(friend,
                                          creditline_ab,
                                          creditline_ba,
                                          interest_ab,
                                          interest_ba,
                                          fees_outstanding_a,
                                          fees_outstanding_b,
                                          mtime,
                                          balance_ab))
            result[user] = list
        return result

    def start_listen_on_full_sync(self, function, sync_interval):
        def sync():
            while True:
                try:
                    function(self.gen_graph_representation())
                    gevent.sleep(sync_interval)
                except socket.timeout as err:
                    logger.warning('Full sync failed because of timeout, try again: ' + str(err))
                    gevent.sleep(reconnect_interval)
                except socket.error as err:
                    logger.warning('Full sync failed because of error, try again: ' + str(err))
                    gevent.sleep(reconnect_interval)

        gevent.Greenlet.spawn(sync)

    def start_listen_on_balance(self, f):
        def log(log_entry):
            f(log_entry['args']['_from'], log_entry['args']['_to'], log_entry['args']['_value'])
        self.start_listen_on(BalanceUpdatedEvent, log)

    def start_listen_on_creditline(self, f):
        def log(log_entry):
            f(log_entry['args']['_creditor'], log_entry['args']['_debtor'], log_entry['args']['_value'])
        self.start_listen_on(CreditlineUpdatedEvent, log)

    def start_listen_on_transfer(self, f):
        def log(log_entry):
            f(log_entry['args']['_from'], log_entry['args']['_to'], log_entry['args']['_value'])
        self.start_listen_on(TransferEvent, log)

    def get_network_events(self, event_name, user_address=None, from_block=0):
        if user_address is None:
            return self.get_events(event_name, from_block=from_block)

        types = {
            TransferEvent: ['_from', '_to'],
            CreditlineRequestEvent: ['_creditor', '_debtor'],
            CreditlineUpdatedEvent: ['_creditor', '_debtor'],
        }
        filter1 = {types[event_name][0]: user_address}
        filter2 = {types[event_name][1]: user_address}

        list_1 = self.get_events(event_name, filter_=filter1, from_block=from_block)
        list_2 = self.get_events(event_name, filter_=filter2, from_block=from_block)
        return list_1 + list_2

    def get_all_network_events(self, user_address=None, from_block=0):
        all_events = []
        for type in CurrencyNetworkProxy.event_types:    # FIXME takes too long.
                                                    # web3.py currently doesn't support getAll() to retrieve all events
            all_events = all_events + self.get_network_events(type, user_address, from_block)
        return all_events

    def estimate_gas_for_transfer(self, sender, receiver, value, max_fee, path):
        return self._proxy.estimateGas({'from': sender}).transfer(receiver, value, max_fee, path)
