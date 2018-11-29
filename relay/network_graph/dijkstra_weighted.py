from heapq import heappush, heappop
from itertools import count
from typing import List
import math

import networkx as nx
import attr
from . import alg


class FeesFirstSenderPaysCostAccumulator(alg.CostAccumulator):
    def __init__(self, value, get_fee, max_hops=None, max_fees=None, ignore=None):
        if max_hops is None:
            max_hops = math.inf
        if max_fees is None:
            max_fees = math.inf

        self.value = value
        self.get_fee = get_fee
        self.max_hops = max_hops
        self.max_fees = max_fees
        self.ignore = ignore

    def zero(self):
        return (0, 0)

    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node, node, dst, graph_data
    ):
        if dst == self.ignore or node == self.ignore:
            return None

        sum_fees, num_hops = cost_from_start_to_node

        if num_hops + 1 > self.max_hops:
            return None

        fee = self.get_fee(graph_data, dst, node, self.value + sum_fees)

        if fee is None or sum_fees + fee > self.max_fees:
            return None

        return (sum_fees + fee, num_hops + 1)


def find_path(G, source, target, get_fee, value, max_hops=None, max_fees=None, ignore=None):
    cost_accumulator = FeesFirstSenderPaysCostAccumulator(
        value, get_fee, max_hops=max_hops, max_fees=max_fees, ignore=ignore)
    cost, path = alg.least_cost_path(
        graph=G,
        starting_nodes={source},
        target_nodes={target},
        cost_accumulator=cost_accumulator)
    return cost[0], path


def find_maximum_capacity_path(G, source, target, get_capacity, max_hops=None):
    """
    The logic is the same as dijkstra's Algorithm
    We visit nodes with the maximum capacity until we reach the destination.
    At this point we are sure it is the maximum capacity path since every path
    already have a smaller capacity and the capacity can only decrease.
    """
    G_adj = G.adj
    push = heappush
    pop = heappop

    paths = {source: [source]}  # dictionary of paths
    capacity = {}  # dictionary of capacities
    seen = {}  # final dictionnaries of capacities
    c = count()
    fringe = []  # use heapq with (distance,label) tuples

    capacity[source] = math.inf
    paths[source] = [source]
    push(fringe, (-math.inf, next(c), source, 0))  # (-capacity, counter, node, hops)
    # We use -capacity because we want the vertex with max capacity

    while fringe:
        (capa, _, u, n) = pop(fringe)
        capa = -capa  # revert the capacity of a vertex to its original meaning
        if u in seen:
            continue  # already searched this node.
        seen[u] = capa
        if u == target:
            break

        for v, e in G_adj[u].items():
            if v in seen:
                continue
            if max_hops is not None:
                if n+1 > max_hops:
                    continue
            else:
                min_cap = min(capacity[u], get_capacity(e, u, v))
                if (v not in capacity) or (v in capacity and capacity[v] < min_cap):
                    capacity[v] = min_cap
                    paths[v] = paths[u]+[v]
                    push(fringe, (-capacity[v], next(c), v, n+1))

    try:
        capacities = []
        u = source

        for v in paths[target][1:]:
            capacity = get_capacity(G[v][u], u, v)
            capacities.append(capacity)
            u = v

        return (seen[target], paths[target], capacities)
        # first element is the total capacity of the path not transferable amount
    except KeyError:
        raise nx.NetworkXNoPath(
            "node %s not reachable from %s" % (source, target))


@attr.s(auto_attribs=True)
class PaymentPath:
    fee: int
    path: List
    value: int
    estimated_gas: int = attr.ib(default=None)
