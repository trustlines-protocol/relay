import csv
import io

import networkx as nx

from relay.dijkstra_weighted import dijkstra_path

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

    @property
    def creditline(self):
        if self.a < self.b:
            return self.data[creditline_ab]
        else:
            return self.data[creditline_ba]

    @property
    def reverse_creditline(self):
        if self.a < self.b:
            return self.data[creditline_ba]
        else:
            return self.data[creditline_ab]

    @balance.setter
    def balance(self, balance):
        if self.a < self.b:
            self.data[creditline_ab] = balance
        else:
            self.data[creditline_ab] = -balance

    @creditline.setter
    def creditline(self, creditline):
        if self.a < self.b:
            self.data[creditline_ab] = creditline
        else:
            self.data[creditline_ba] = creditline

    @reverse_creditline.setter
    def reverse_creditline(self, creditline):
        if self.a < self.b:
            self.data[creditline_ba] = creditline
        else:
            self.data[creditline_ab] = creditline

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
    def creditline_left_received(self):
        return self.balance + self.creditline_received

    def as_dict(self):
        return {'balance': self.balance,
                'given': self.creditline_given,
                'received': self.creditline_received,
                'leftGiven': self.creditline_left_given,
                'leftReceived' : self.creditline_left_received}


class Friendship(object):
    """Representing Friendship to address"""
    def __init__(self, address, creditline_ab, creditline_ba, balance_ab):
        self.address = address
        self.creditline_ab = creditline_ab
        self.creditline_ba = creditline_ba
        self.balance_ab = balance_ab

    def __repr__(self):
        return '([{}]({},{},{})'.format(self.address, self.creditline_ab, self.creditline_ba, self.balance_ab)


class CurrencyNetworkGraph(object):
    """The whole graph of a Token Network"""

    def __init__(self):
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
        return sum([abs(edge[2]) for edge in self.graph.edges_iter(data = balance_ab)])

    @property
    def total_creditlines(self):
        return sum([edge[2] for edge in self.graph.edges_iter(data = creditline_ab)])\
               + sum([edge[2] for edge in self.graph.edges_iter(data=creditline_ba)])

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
                                balance_ab=0,
                                )
        account = Account(self.graph[creditor][debtor], creditor, debtor)
        account.creditline = creditline

    def update_balance(self, a, b, balance):
        """to update the balance, used to react on changes on the blockchain"""
        if not self.graph.has_edge(a, b):
            self.graph.add_edge(a,
                                b,
                                creditline_ab=0,
                                creditline_ba=0,
                                balance_ab=0,
                                )
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
        output = io.BytesIO()
        fieldnames = ['Address A', 'Address B', 'Balance AB', 'Creditline AB', 'Creditline BA']
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for u, v, d in self.graph.edges(data=True):
            account = Account(d, u, v)
            writer.writerow({ 'Address A': account.a,
                              'Address B': account.b,
                              'Balance AB': account.balance,
                              'Creditline AB': account.creditline,
                              'Creditline BA': account.reverse_creditline})
        return output.getvalue()

    @staticmethod
    def _get_path_cost_function(value, hop_cost=1, imbalance_cost_factor=.5):
        """
        goal: from all possible paths, choose from the shortes the one which rebalances the best
        """

        def cost_func_fast(a, b, data):
            # this func should be as fast as possible, as it's called often
            # don't use Account which allocs memory
            if a < b:
                pre_balance = data[balance_ab]
                creditline = data[creditline_ba]
            else:
                pre_balance = -data[balance_ab]
                creditline = data[creditline_ab]
            post_balance = pre_balance - value
            # assert abs(pre_balance) <= _account['creditline']
            if -post_balance > creditline:
                return None  # no valid path
            # FIXME division Zero
            # imbalance_cost = (abs(post_balance) - abs(pre_balance)) / creditline
            imbalance_cost = 1
            # assert -1 <= imbalance_cost <= 1
            cost = hop_cost + imbalance_cost_factor * imbalance_cost
            # assert cost > 0
            return cost

        return cost_func_fast

    def find_path(self, source, target, value):
        """
        find path between source and target
        the shortest path is found based on
            - the number of hops
            - the imbalance it adds or reduces in the accounts
        """

        try:
            path = dijkstra_path(self.graph, source, target, self._get_path_cost_function(value))
        except (nx.NetworkXNoPath, KeyError): # key error for if source or target is not in graph
            path = []
        return path

    def calc_path_cost(self, path, value):
        path = list(path)  # copy
        cost_func = self._get_path_cost_function(value)
        cost = 0
        source = path.pop(0)
        while path:
            target = path.pop(0)
            cost += cost_func(source, target, self.graph.edge[source][target]) or 0  # FIXME
            source = target
        return cost

    def transfer(self, source, target, value):
        """simulate transfer off chain"""
        account = Account(self.graph[source][target], source, target)
        account.balance -= value

    def mediated_transfer(self, source, target, value):
        """simulate mediated transfer off chain"""
        path = self.find_path(source, target, value)
        assert path[0] == source
        assert path[-1] == target
        cost = self.calc_path_cost(path, value)
        source = path.pop(0)
        while len(path):
            target = path.pop(0)
            self.transfer(source, target, value)
            source = target
        return cost
