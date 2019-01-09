import csv
import io
import time
import math
from typing import Iterable, Any, NamedTuple

import networkx as nx

from relay.network_graph.trustline_data import (
    get_balance,
    set_balance,
    get_mtime,
    set_mtime,
    get_creditline,
    set_creditline,
    get_interest_rate,
    set_interest_rate,
    get_fees_outstanding,
    set_fees_outstanding
)

from .dijkstra_weighted import (
    PaymentPath
)

from .fees import (calculate_fees_reverse, calculate_fees, imbalance_generated)
from .interests import balance_with_interests
from relay.network_graph.graph_constants import (
    creditline_ab,
    creditline_ba,
    balance_ab,
)

from . import alg


class NetworkGraphConfig(NamedTuple):
    capacity_imbalance_fee_divisor: int = 0
    trustlines: Iterable = []


class Account(object):
    """account from the view of a"""

    def __init__(self, data, user, counter_party):
        self.a = user
        self.b = counter_party
        self.data = data

    @property
    def balance(self) -> int:
        """Returns the balance without interests"""
        return get_balance(self.data, self.a, self.b)

    @balance.setter
    def balance(self, balance: int):
        set_balance(self.data, self.a, self.b, balance)

    def balance_with_interests(self, timestamp_in_seconds: int) -> int:
        """Returns the balance at a given time with an estimation of the interests"""
        return balance_with_interests(self.balance,
                                      self.interest_rate,
                                      self.reverse_interest_rate,
                                      timestamp_in_seconds - self.m_time)

    @property
    def m_time(self) -> int:
        return get_mtime(self.data)

    @m_time.setter
    def m_time(self, timestamp: int):
        set_mtime(self.data, timestamp)

    @property
    def creditline(self):
        return get_creditline(self.data, self.a, self.b)

    @creditline.setter
    def creditline(self, creditline):
        set_creditline(self.data, self.a, self.b, creditline)

    @property
    def reverse_creditline(self):
        return get_creditline(self.data, self.b, self.a)

    @reverse_creditline.setter
    def reverse_creditline(self, creditline):
        set_creditline(self.data, self.b, self.a, creditline)

    @property
    def interest_rate(self):
        return get_interest_rate(self.data, self.a, self.b)

    @interest_rate.setter
    def interest_rate(self, interest_rate):
        set_interest_rate(self.data, self.a, self.b, interest_rate)

    @property
    def reverse_interest_rate(self):
        return get_interest_rate(self.data, self.b, self.a)

    @reverse_interest_rate.setter
    def reverse_interest_rate(self, interest_rate):
        set_interest_rate(self.data, self.b, self.a, interest_rate)

    @property
    def fees_outstanding(self):
        return get_fees_outstanding(self.data, self.a, self.b)

    @fees_outstanding.setter
    def fees_outstanding(self, fees):
        set_fees_outstanding(self.data, self.a, self.b, fees)

    @property
    def reverse_fees_outstanding(self):
        return get_fees_outstanding(self.data, self.b, self.a)

    @reverse_fees_outstanding.setter
    def reverse_fees_outstanding(self, fees):
        set_fees_outstanding(self.data, self.b, self.a, fees)

    def __repr__(self):
        return 'Account({}, {}, {})'.format(self.a, self.b, self.data)


class AccountSummary(object):
    """Representing an account summary"""

    def __init__(self, balance=0, creditline_given=0, creditline_received=0):
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


class AccountSummaryWithInterests(AccountSummary):
    """Representing an account summary with interests """

    def __init__(self,
                 balance=0,
                 creditline_given=0,
                 creditline_received=0,
                 interest_rate_given=0,
                 interests_received=0):
        super().__init__(balance, creditline_given, creditline_received)
        self.interest_rate_given = interest_rate_given
        self.interest_rate_received = interests_received


class SenderPaysCostAccumulatorSnapshot(alg.CostAccumulator):
    """This is the CostAccumulator being used when using our default 'sender
    pays fees' style of payments"

    This sorts by the fees first, then the number of hops.

    We need to pass a timestamp in the constructor. This is being used to
    compute a consistent view of balances in the trustlines network.

    To find the correct fee, the pathfinding has to be done in reverse from receiver to sender
    as we only know the value to be received at the beginning
    """

    class Cost(NamedTuple):
        fees: int
        num_hops: int

    def __init__(self, *, timestamp, value, capacity_imbalance_fee_divisor, max_hops=None, max_fees=None, ignore=None):
        if max_hops is None:
            max_hops = math.inf
        if max_fees is None:
            max_fees = math.inf

        self.timestamp = timestamp
        self.value = value
        self.capacity_imbalance_fee_divisor = capacity_imbalance_fee_divisor
        self.max_hops = max_hops
        self.max_fees = max_fees
        self.ignore = ignore

    def zero(self):
        return self.Cost(0, 0)

    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node, node, dst, edge_data
    ):
        if dst == self.ignore or node == self.ignore:
            return None

        sum_fees, num_hops = cost_from_start_to_node

        if num_hops + 1 > self.max_hops:
            return None

        # fee computation has been inlined here, since the comment in
        # Graph._get_fee suggests it should be as fast as possible. This means
        # we do have some code duplication, but I couldn't use some of the
        # methods in Graph anyway, because they don't take a timestamp argument
        # and rather use the current time.
        #
        # We should profile this at some point in time.
        #
        # We do the pathfinding in reverse, when the sender pays. In this
        # method this means that the payment is done from dst to node, i.e. the
        # order of arguments node and dst is reversed in the following code

        pre_balance = balance_with_interests(
            get_balance(edge_data, dst, node),
            get_interest_rate(edge_data, dst, node),
            get_interest_rate(edge_data, node, dst),
            self.timestamp - get_mtime(edge_data))

        if num_hops == 0:
            fee = 0
        else:
            fee = calculate_fees_reverse(
                imbalance_generated=imbalance_generated(value=self.value + sum_fees, balance=pre_balance),
                capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor)

        if sum_fees + fee > self.max_fees:
            return None

        # check that we don't exceed the creditline
        capacity = pre_balance + get_creditline(edge_data, node, dst)
        if self.value + sum_fees + fee > capacity:
            return None  # creditline exceeded

        return self.Cost(fees=sum_fees + fee, num_hops=num_hops + 1)


class ReceiverPaysCostAccumulatorSnapshot(alg.CostAccumulator):
    """This is the CostAccumulator being used when using our 'receiver pays
    fees' style of payments"

    This sorts by the fees first, then the
    number of hops, then the fee for the previous hop.


    We need to pass a timestamp in the constructor. This is being used to
    compute a consistent view of balances in the trustlines network.

    To find the right fee, the pathfinding has to be done from sender to receiver
    as we only know the value to be sent at the beginning
    """

    class Cost(NamedTuple):
        fees: int
        num_hops: int
        previous_hop_fee: int

    def __init__(self, *, timestamp, value, capacity_imbalance_fee_divisor, max_hops=None, max_fees=None, ignore=None):
        if max_hops is None:
            max_hops = math.inf
        if max_fees is None:
            max_fees = math.inf

        self.timestamp = timestamp
        self.value = value
        self.capacity_imbalance_fee_divisor = capacity_imbalance_fee_divisor
        self.max_hops = max_hops
        self.max_fees = max_fees
        self.ignore = ignore

    def zero(self):
        return self.Cost(0, 0, 0)

    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node: Cost, node, dst, edge_data
    ):
        if dst == self.ignore or node == self.ignore:
            return None

        # For this case the pathfinding is not done in reverse.
        #
        # we maintain the computed fee for the previous hop, since that is only
        # 'paid out' when we jump to the next hop The first element in this
        # tuple has to be the sum of the fees not including the fee for the
        # previous hop, since the graph finding algorithm needs to sort by that
        # and not by what would be paid out if there is another hop
        sum_fees, num_hops, previous_hop_fee = cost_from_start_to_node

        if num_hops + 1 > self.max_hops:
            return None

        pre_balance = balance_with_interests(
            get_balance(edge_data, node, dst),
            get_interest_rate(edge_data, node, dst),
            get_interest_rate(edge_data, dst, node),
            self.timestamp - get_mtime(edge_data))

        fee = calculate_fees(
            imbalance_generated=imbalance_generated(
                value=self.value - sum_fees - previous_hop_fee,
                balance=pre_balance),
            capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor)

        if sum_fees + previous_hop_fee > self.max_fees:
            return None

        # check that we don't exceed the creditline
        capacity = pre_balance + get_creditline(edge_data, dst, node)
        if self.value - sum_fees - previous_hop_fee > capacity:
            return None  # creditline exceeded

        return self.Cost(fees=sum_fees + previous_hop_fee, num_hops=num_hops + 1, previous_hop_fee=fee)


class SenderPaysCapacityAccumulator(alg.CostAccumulator):
    """This is being used to find a path with the maximum capacity

    This sorts by the capacity first, then the
    number of hops, then the fee for the previous hop.


    We need to pass a timestamp in the constructor. This is being used to
    compute a consistent view of balances in the trustlines network.

    To find the right maximum capacity, the pathfinding has to be done from sender to receiver
    as we want to find out the maximum amount the receiver can receive
    """

    class Cost(NamedTuple):
        minus_capacity: int
        num_hops: int
        previous_hop_fee: int

    def __init__(self, *, timestamp, capacity_imbalance_fee_divisor, max_hops=None):
        if max_hops is None:
            max_hops = math.inf
        self.max_hops = max_hops
        self.timestamp = timestamp
        self.capacity_imbalance_fee_divisor = capacity_imbalance_fee_divisor

    def get_balance(self, node, dst, edge_data):
        return balance_with_interests(
            get_balance(edge_data, node, dst),
            get_interest_rate(edge_data, node, dst),
            get_interest_rate(edge_data, dst, node),
            self.timestamp - get_mtime(edge_data))

    def get_capacity(self, node, dst, edge_data):
        return self.get_balance(node, dst, edge_data) + get_creditline(edge_data, dst, node)

    def zero(self):
        # We use (- capacity, num_hops, last_hop_fee) as cost
        # last hop fee is only passed to have it available, not to optimize for it
        return self.Cost(-math.inf, 0, 0)

    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node: Cost, node, dst, edge_data
    ):

        capacity_from_start_to_node = - cost_from_start_to_node.minus_capacity
        num_hops = cost_from_start_to_node.num_hops
        previous_hop_fee = cost_from_start_to_node.previous_hop_fee

        if num_hops + 1 > self.max_hops:
            return None

        capacity_this_edge = min(
            self.get_capacity(node, dst, edge_data),
            capacity_from_start_to_node - previous_hop_fee)

        fee = calculate_fees(
            imbalance_generated=imbalance_generated(
                value=capacity_this_edge,
                balance=self.get_balance(node, dst, edge_data)),
            capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor)

        return self.Cost(minus_capacity=-capacity_this_edge, num_hops=num_hops + 1, previous_hop_fee=fee)


class CurrencyNetworkGraph(object):
    """The whole graph of a Token Network"""

    def __init__(self, capacity_imbalance_fee_divisor=0, default_interest_rate=0,
                 custom_interests=False, prevent_mediator_interests=False):

        self.capacity_imbalance_fee_divisor = capacity_imbalance_fee_divisor
        self.default_interest_rate = default_interest_rate
        self.custom_interests = custom_interests
        self.prevent_mediator_interests = prevent_mediator_interests
        self.graph = nx.Graph()

    def gen_network(self, trustlines: Iterable[Any]):
        self.graph.clear()
        for trustline in trustlines:
            assert trustline.user < trustline.counter_party
            self.graph.add_edge(trustline.user,
                                trustline.counter_party,
                                creditline_ab=trustline.creditline_given,
                                creditline_ba=trustline.creditline_received,
                                interest_ab=trustline.interest_rate_given,
                                interest_ba=trustline.interest_rate_received,
                                fees_outstanding_a=trustline.fees_outstanding_user,
                                fees_outstanding_b=trustline.fees_outstanding_counter_party,
                                m_time=trustline.m_time,
                                balance_ab=trustline.balance,
                                )

    @classmethod
    def from_config(cls, config: NetworkGraphConfig):
        currency_network_graph = CurrencyNetworkGraph(
            capacity_imbalance_fee_divisor=config.capacity_imbalance_fee_divisor
        )
        currency_network_graph.gen_network(config.trustlines)
        return currency_network_graph

    @property
    def users(self):
        return list(self.graph.nodes())

    @property
    def money_created(self):
        return sum([abs(edge[2]) for edge in self.graph.edges(data=balance_ab)])  # does not include interests

    @property
    def has_interests(self) -> bool:
        return self.custom_interests or self.default_interest_rate > 0

    @property
    def total_creditlines(self):
        return sum([edge[2] for edge in self.graph.edges(data=creditline_ab)])\
               + sum([edge[2] for edge in self.graph.edges(data=creditline_ba)])

    def get_friends(self, address):
        if address in self.graph:
            return self.graph[address].keys()
        else:
            return []

    def update_trustline(self, creditor, debtor, creditline_given: int, creditline_received: int,
                         interest_rate_given: int = None, interest_rate_received: int = None, timestamp: int = None):
        """to update the creditlines, used to react on changes on the blockchain"""
        if not self.graph.has_edge(creditor, debtor):
            self.graph.add_edge(creditor,
                                debtor,
                                creditline_ab=0,
                                creditline_ba=0,
                                interest_ab=self.default_interest_rate,
                                interest_ba=self.default_interest_rate,
                                fees_outstanding_a=0,
                                fees_outstanding_b=0,
                                m_time=0,
                                balance_ab=0)
        account = Account(self.graph[creditor][debtor], creditor, debtor)
        account.creditline = creditline_given
        account.reverse_creditline = creditline_received

        if interest_rate_given is not None:
            account.interest_rate = interest_rate_given
        elif self.custom_interests:
            raise RuntimeError('Not interests specified even though custom interests are enabled')

        if interest_rate_received is not None:
            account.reverse_interest_rate = interest_rate_received
        elif self.custom_interests:
            raise RuntimeError('Not interests specified even though custom interests are enabled')

        if timestamp is not None:
            account.m_time = timestamp
        elif self.has_interests:
            raise RuntimeError('No timestamp was given. When using interests a timestamp is mandatory')

    def get_balance_with_interests(self, a, b, timestamp):
        if not self.graph.has_edge(a, b):
            return 0
        return Account(self.graph[a][b], a, b).balance_with_interests(timestamp)

    def update_balance(self, a: str, b: str, balance: int, timestamp: int = None):
        """to update the balance, used to react on changes on the blockchain
        the last modification time of the balance is also updated to keep track of the interests"""
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
        if timestamp is not None:
            account.m_time = timestamp
        elif self.has_interests:
            raise RuntimeError('No timestamp was given. When using interests a timestamp is mandatory')

    def get_account_sum(self, user, counter_party=None, timestamp=None):
        if timestamp is None:
            timestamp = int(time.time())

        if counter_party is None:
            account_summary = AccountSummary()
            for counter_party in self.get_friends(user):
                account = Account(self.graph[user][counter_party], user, counter_party)
                account_summary.balance += account.balance_with_interests(timestamp)
                account_summary.creditline_given += account.creditline
                account_summary.creditline_received += account.reverse_creditline
            return account_summary
        else:
            if self.graph.has_edge(user, counter_party):
                account = Account(self.graph[user][counter_party], user, counter_party)
                return AccountSummaryWithInterests(account.balance_with_interests(timestamp),
                                                   account.creditline, account.reverse_creditline,
                                                   account.interest_rate, account.reverse_interest_rate)
            else:
                return AccountSummaryWithInterests()

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

    def find_path(self, source, target, value=None, max_hops=None, max_fees=None, timestamp=None):
        """
        find path between source and target
        the shortest path is found based on
            - the number of hops
            - the imbalance it adds or reduces in the accounts
        """
        if value is None:
            value = 1
        if timestamp is None:
            timestamp = int(time.time())

        cost_accumulator = SenderPaysCostAccumulatorSnapshot(
            timestamp=timestamp,
            value=value,
            capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor,
            max_hops=max_hops,
            max_fees=max_fees)

        try:
            # we are searching in reverse, so source and target are swapped!
            cost, path = alg.least_cost_path(
                graph=self.graph,
                starting_nodes={target},
                target_nodes={source},
                cost_accumulator=cost_accumulator
            )
        except (nx.NetworkXNoPath, KeyError):  # key error for if source or target is not in graph
            return 0, []
        return cost[0], list(reversed(path))

    def close_trustline_path_triangulation(self, timestamp, source, target, max_hops=None, max_fees=None):
        neighbors = {x[0] for x in self.graph.adj[source].items()} - {target}
        balance = self.get_balance_with_interests(source, target, timestamp)
        value = abs(balance)
        if max_hops is not None:
            max_hops -= 2  # we compute the path without source at the beginning and end

        if balance == 0:
            return PaymentPath(fee=0, path=[], value=0)
        elif balance < 0:
            # payment looks like
            #
            #   source -> neighbor -> ... -> target -> source
            #
            # since in this case we use sender pays, we search in reverse from
            # target to neighbor
            cost_accumulator_class = SenderPaysCostAccumulatorSnapshot
        elif balance > 0:
            # payment looks like
            #
            # source -> target -> ... -> neighbor -> source
            #
            # in this case we use receiver pays, so we search in right order
            # from target to neighbor
            cost_accumulator_class = ReceiverPaysCostAccumulatorSnapshot

        cost_accumulator = cost_accumulator_class(
            timestamp=timestamp,
            value=value,
            capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor,
            max_hops=max_hops,
            max_fees=max_fees,
            ignore=source)

        try:
            # can't use the cost as returned by alg.least_cost_path since it
            # doesn't include the source node at the beginning and end
            _, path = alg.least_cost_path(
                graph=self.graph,
                starting_nodes={target},
                target_nodes=neighbors,
                cost_accumulator=cost_accumulator)
            path = [source] + path + [source]
            cost_accumulator.ignore = None  # hackish, but otherwise the following compute_cost_for_path won't work
            cost_accumulator.max_hops = math.inf  # don't check max_hops, we know we're below
            cost = cost_accumulator.compute_cost_for_path(self.graph, path)
        except nx.NetworkXNoPath:
            return PaymentPath(fee=0, path=[], value=value)

        if balance < 0:
            path.reverse()

        return PaymentPath(fee=cost[0], path=path, value=value)

    def find_maximum_capacity_path(self, source, target, max_hops=None, timestamp=None):
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
        if timestamp is None:
            timestamp = int(time.time())
        capacity_accumulator = SenderPaysCapacityAccumulator(
            timestamp=timestamp,
            capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor,
            max_hops=max_hops
        )

        try:
            cost, path = alg.least_cost_path(
                graph=self.graph,
                starting_nodes={source},
                target_nodes={target},
                cost_accumulator=capacity_accumulator)
        except (nx.NetworkXNoPath, KeyError):  # key error for if source or target is not in graph
            return 0, []

        return -cost[0], list(path)

    def get_balances_along_path(self, path):
        balances = []

        for i in range(0, len(path) - 1):
            data = self.graph.get_edge_data(path[i], path[i+1])
            balances.append(get_balance(data, path[i], path[i+1]))

        return balances


class CurrencyNetworkGraphForTesting(CurrencyNetworkGraph):
    """A currency network graph with some additional methods used for testing"""
    def __init__(self, capacity_imbalance_fee_divisor=0, default_interest_rate=0,
                 custom_interests=False, prevent_mediator_interests=False):
        super().__init__(
            capacity_imbalance_fee_divisor=capacity_imbalance_fee_divisor,
            default_interest_rate=default_interest_rate,
            custom_interests=custom_interests,
            prevent_mediator_interests=prevent_mediator_interests)

    def transfer_path(self, path, value, expected_fees):
        assert value > 0
        cost_accumulator = SenderPaysCostAccumulatorSnapshot(
            timestamp=int(time.time()),
            value=value,
            capacity_imbalance_fee_divisor=self.capacity_imbalance_fee_divisor)
        cost = cost_accumulator.zero()

        path = list(reversed(path))
        for source, target in zip(path, path[1:]):
            edge_data = self.graph.get_edge_data(source, target)
            cost = cost_accumulator.total_cost_from_start_to_dst(
                cost, source, target, edge_data,
            )
            if cost is None:
                raise nx.NetworkXNoPath("no path found")
            new_balance = get_balance(edge_data, target, source) - value - cost[0]
            set_balance(edge_data, target, source, new_balance)

        assert expected_fees == cost[0]
        return cost[0]

    def mediated_transfer(self, source, target, value):
        """simulate mediated transfer off chain"""
        cost, path = self.find_path(source, target, value)
        assert path[0] == source
        assert path[-1] == target
        return self.transfer_path(path, value, cost)
