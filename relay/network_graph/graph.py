import csv
import io

import networkx as nx

from .dijkstra_weighted import find_path, find_path_triangulation, find_maximum_capacity_path
from .fees import new_balance, imbalance_fee, estimate_fees_from_capacity

creditline_ab = 'creditline_ab'
creditline_ba = 'creditline_ba'
interest_ab = 'interest_ab'
interest_ba = 'interest_ba'
fees_outstanding_a = 'fees_outstanding_a'
fees_outstanding_b = 'fees_outstanding_b'
m_time = 'm_time'
balance_ab = 'balance_ab'


class Account(object):
    """account from the view of a"""

    def __init__(self, data, src, dest):
        self.a = src
        self.b = dest
        self.data = data

    @property
    def balance(self):
        if self.a < self.b:
            return self.data[balance_ab]
        else:
            return -self.data[balance_ab]

    @balance.setter
    def balance(self, balance):
        if self.a < self.b:
            self.data[balance_ab] = balance
        else:
            self.data[balance_ab] = -balance

    @property
    def creditline(self):
        if self.a < self.b:
            return self.data[creditline_ab]
        else:
            return self.data[creditline_ba]

    @creditline.setter
    def creditline(self, creditline):
        if self.a < self.b:
            self.data[creditline_ab] = creditline
        else:
            self.data[creditline_ba] = creditline

    @property
    def reverse_creditline(self):
        if self.a < self.b:
            return self.data[creditline_ba]
        else:
            return self.data[creditline_ab]

    @reverse_creditline.setter
    def reverse_creditline(self, creditline):
        if self.a < self.b:
            self.data[creditline_ba] = creditline
        else:
            self.data[creditline_ab] = creditline

    @property
    def interest(self):
        if self.a < self.b:
            return self.data[interest_ab]
        else:
            return self.data[interest_ba]

    @interest.setter
    def interest(self, interest):
        if self.a < self.b:
            self.data[interest_ab] = interest
        else:
            self.data[interest_ba] = interest

    @property
    def reverse_interest(self):
        if self.a < self.b:
            return self.data[interest_ba]
        else:
            return self.data[interest_ab]

    @reverse_interest.setter
    def reverse_interest(self, interest):
        if self.a < self.b:
            self.data[interest_ba] = interest
        else:
            self.data[interest_ab] = interest

    @property
    def fees_outstanding(self):
        if self.a < self.b:
            return self.data[fees_outstanding_a]
        else:
            return self.data[fees_outstanding_b]

    @fees_outstanding.setter
    def fees_outstanding(self, fees):
        if self.a < self.b:
            self.data[fees_outstanding_a] = fees
        else:
            self.data[fees_outstanding_b] = fees

    @property
    def reverse_fees_outstanding(self):
        if self.a < self.b:
            return self.data[fees_outstanding_b]
        else:
            return self.data[fees_outstanding_a]

    @reverse_fees_outstanding.setter
    def reverse_fees_outstanding(self, fees):
        if self.a < self.b:
            self.data[fees_outstanding_b] = fees
        else:
            self.data[fees_outstanding_a] = fees

    def __repr__(self):
        return '<Account(balance:{} creditline:{}>'.format(self.balance, self.creditline)


class AccountSummary(object):
    """Representing an account summary"""

    def __init__(self, balance, creditline_given, creditline_received):
        self.balance = balance
        self.creditline_given = creditline_given
        self.creditline_received = creditline_received

    @property
    def creditline_left_given(self):
        return -self.balance + self.creditline_given

    @property
    def available(self):
        return self.creditline_left_received

    @property
    def creditline_left_received(self):
        return self.balance + self.creditline_received


class CurrencyNetworkGraph(object):
    """The whole graph of a Token Network"""

    def __init__(self, capacity_imbalance_fee_divisor=0):
        self.capacity_imbalance_fee_divisor = capacity_imbalance_fee_divisor
        self.graph = nx.Graph()

    def gen_network(self, friendsdict):
        self.graph.clear()
        for address, friendships in friendsdict.items():
            for friendship in friendships:
                assert address < friendship.address
                self.graph.add_edge(address,
                                    friendship.address,
                                    creditline_ab=friendship.creditline_ab,
                                    creditline_ba=friendship.creditline_ba,
                                    interest_ab=friendship.interest_ab,
                                    interest_ba=friendship.interest_ba,
                                    fees_outstanding_a=friendship.fees_outstanding_a,
                                    fees_outstanding_b=friendship.fees_outstanding_b,
                                    m_time=friendship.m_time,
                                    balance_ab=friendship.balance_ab,
                                    )

    @property
    def users(self):
        return self.graph.nodes()

    @property
    def money_created(self):
        return sum([abs(edge[2]) for edge in self.graph.edges(data=balance_ab)])

    @property
    def total_creditlines(self):
        return sum([edge[2] for edge in self.graph.edges(data=creditline_ab)])\
               + sum([edge[2] for edge in self.graph.edges(data=creditline_ba)])

    def get_friends(self, address):
        if address in self.graph:
            return self.graph[address].keys()
        else:
            return []

    def update_creditline(self, creditor, debtor, creditline):
        """to update the creditline, used to react on changes on the blockchain"""
        if not self.graph.has_edge(creditor, debtor):
            self.graph.add_edge(creditor,
                                debtor,
                                creditline_ab=0,
                                creditline_ba=0,
                                interest_ab=0,
                                interest_ba=0,
                                fees_outstanding_a=0,
                                fees_outstanding_b=0,
                                m_time=0,
                                balance_ab=0)
        account = Account(self.graph[creditor][debtor], creditor, debtor)
        account.creditline = creditline

    def update_trustline(self, creditor, debtor, creditline_given, creditline_received):
        """to update the creditlines, used to react on changes on the blockchain"""
        if not self.graph.has_edge(creditor, debtor):
            self.graph.add_edge(creditor,
                                debtor,
                                creditline_ab=0,
                                creditline_ba=0,
                                interest_ab=0,
                                interest_ba=0,
                                fees_outstanding_a=0,
                                fees_outstanding_b=0,
                                m_time=0,
                                balance_ab=0)
        account = Account(self.graph[creditor][debtor], creditor, debtor)
        account.creditline = creditline_given
        account.reverse_creditline = creditline_received

    def update_balance(self, a, b, balance):
        """to update the balance, used to react on changes on the blockchain"""
        if not self.graph.has_edge(a, b):
            self.graph.add_edge(a,
                                b,
                                creditline_ab=0,
                                creditline_ba=0,
                                interest_ab=0,
                                interest_ba=0,
                                fees_outstanding_a=0,
                                fees_outstanding_b=0,
                                m_time=0,
                                balance_ab=0)
        account = Account(self.graph[a][b], a, b)
        account.balance = balance

    def get_account_sum(self, a, b=None):
        if b is None:
            account_summary = AccountSummary(0, 0, 0)
            for b in self.get_friends(a):
                account = Account(self.graph[a][b], a, b)
                accountr = Account(self.graph[b][a], b, a)
                account_summary.balance += account.balance
                account_summary.creditline_given += account.creditline
                account_summary.creditline_received += accountr.creditline
            return account_summary
        else:
            if self.graph.has_edge(a, b):
                account = Account(self.graph[a][b], a, b)
                accountr = Account(self.graph[b][a], b, a)
                return AccountSummary(account.balance, account.creditline, accountr.creditline)
            else:
                return AccountSummary(0, 0, 0)

    def draw(self, filename):
        """draw graph to a file called filename"""
        def mapping(address):
            return address[2:6] if len(address) > 6 else address[2:]
        for u, v, d in self.graph.edges(data=True):
            self.graph.node[u]['width'] = 0.6
            self.graph.node[u]['height'] = 0.4
            d['color'] = 'blue'
            d['len'] = 1.4
        g = nx.relabel_nodes(self.graph, mapping)
        a = nx.drawing.nx_agraph.to_agraph(g)
        a.graph_attr['label'] = 'Trustlines Network'
        a.layout()
        a.draw(filename)

    def dump(self):
        output = io.StringIO()
        fieldnames = ['Address A', 'Address B', 'Balance AB', 'Creditline AB', 'Creditline BA']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for u, v, d in self.graph.edges(data=True):
            account = Account(d, u, v)
            writer.writerow({'Address A': account.a,
                             'Address B': account.b,
                             'Balance AB': account.balance,
                             'Creditline AB': account.creditline,
                             'Creditline BA': account.reverse_creditline})
        return output.getvalue()

    def _cost_func_fast_reverse(self, b, a, data, value):
        # this func should be as fast as possible, as it's called often
        # don't use Account which allocs memory
        if a < b:
            pre_balance = data[balance_ab]
            creditline = data[creditline_ba]
        else:
            pre_balance = -data[balance_ab]
            creditline = data[creditline_ab]
        post_balance = new_balance(self.capacity_imbalance_fee_divisor, pre_balance, value)
        assert post_balance <= pre_balance
        if -post_balance > creditline:
            return None  # no valid path
        cost = imbalance_fee(self.capacity_imbalance_fee_divisor, pre_balance, value)
        assert cost >= 0
        return cost

    def find_path(self, source, target, value=None, max_hops=None, max_fees=None):
        """
        find path between source and target
        the shortest path is found based on
            - the number of hops
            - the imbalance it adds or reduces in the accounts
        """
        if value is None:
            value = 1
        try:
            cost, path = find_path(self.graph,
                                   target, source,
                                   self._cost_func_fast_reverse,
                                   value,
                                   max_hops=max_hops,
                                   max_fees=max_fees)
        except (nx.NetworkXNoPath, KeyError):  # key error for if source or target is not in graph
            cost, path = 0, []
            # cost is the total fee, not the actual amount to be transfered
        return cost, list(reversed(path))

    def find_path_triangulation(self, source, target_reduce, target_increase,
                                value=None, max_hops=None, max_fees=None):
        """
        find a path to update the the creditline between source and target with value, via target_increasae
        the shortest path is found based on
            - the number of hops
            - the imbalance it adds or reduces in the accounts
        """
        if value is None:
            value = 1
        try:
            cost, path = find_path_triangulation(self.graph,
                                                 source,
                                                 target_reduce,
                                                 target_increase,
                                                 self._cost_func_fast_reverse,
                                                 value,
                                                 max_hops=max_hops,
                                                 max_fees=max_fees)
        except (nx.NetworkXNoPath, KeyError):  # key error for if source or target is not in graph
            cost, path = 0, []  # cost is the total fee, not the actual amount to be transfered
        return cost, list(path)

    def find_maximum_capacity_path(self, source, target, max_hops=None):
        """
        find a path probably with the maximum capacity to transfer from source to target
        The "imbalance_fee" function not being bijective, only an estimate of the fees can be found from "value + fee"

        Args:
            source: source for the path
            target: target for the path
            max_hops: the maximum number of hops to find the path

        Returns:
            returns the value that can be send in the max capacity path and the path,
        """
        try:
            min_capacity, path, path_capacities = find_maximum_capacity_path(self.graph,
                                                                             source,
                                                                             target,
                                                                             max_hops=max_hops)
        except (nx.NetworkXNoPath, KeyError):  # key error for if source or target is not in graph
            min_capacity, path, path_capacities = 0, [], []

        sendable = self.estimate_sendable_from_capacity(min_capacity, path_capacities)

        if sendable <= 0:
            return 0, []

        return sendable, list(path)

    def estimate_sendable_from_capacity(self, capacity, path_capacities):
        """
        estimates the actual sendable amount along a path with path_capacities;
        capacity is the smallest value of path_capacities
        """
        divisor = self.capacity_imbalance_fee_divisor

        if divisor == 0:
            return capacity

        fees = estimate_fees_from_capacity(self.capacity_imbalance_fee_divisor, capacity, path_capacities)

        # we treat the edge case that bothers us so much here.
        if capacity//divisor == capacity % divisor:
            capacity -= 1

        return capacity - fees

    def transfer(self, source, target, value):
        """simulate transfer off chain"""
        account = Account(self.graph[source][target], source, target)
        fee = imbalance_fee(self.capacity_imbalance_fee_divisor, account.balance, value)
        account.balance = new_balance(self.capacity_imbalance_fee_divisor, account.balance, value)
        return fee

    def transfer_path(self, path, value, cost):
        path = list(reversed(path))
        fees = 0
        target = path.pop(0)
        while len(path):
            source = path.pop(0)
            fee = self.transfer(source, target, value)
            value += fee
            fees += fee
            target = source
        assert fees == cost
        return cost

    def mediated_transfer(self, source, target, value):
        """simulate mediated transfer off chain"""
        cost, path = self.find_path(source, target, value)
        assert path[0] == source
        assert path[-1] == target
        return self.transfer_path(path, value, cost)

    def triangulation_transfer(self, source, target_reduce, target_increase, value):
        """simulate triangulation transfer off chain"""
        cost, path = self.find_path_triangulation(source, target_reduce, target_increase, value)
        assert path[0] == source
        assert path[-1] == source
        return self.transfer_path(path, value, cost)
