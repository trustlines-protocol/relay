from heapq import heappush, heappop
from itertools import count
from typing import List
import math

import networkx as nx
import attr


def find_path(G, source, target, get_fee, value, max_hops=None, max_fees=None, ignore=None):
    G_adj = G.adj

    paths = {source: [source]}  # dictionary of paths

    push = heappush
    pop = heappop
    dist = {}  # dictionary of final distances
    dist_hop = {}  # dictionary of final distances in terms of hops
    seen = {source: value}
    c = count()
    fringe = []  # use heapq with (distance,label) tuples
    push(fringe, (0, value, next(c), source))
    while fringe:
        (n, d, _, v) = pop(fringe)
        if v in dist:
            continue  # already searched this node.
        if v == ignore:
            continue
        dist[v] = d
        dist_hop[v] = n
        if v == target:
            break

        for u, e in G_adj[v].items():
            cost = get_fee(e, u, v, d)  # fee of transferring from u to v
            if cost is None:
                continue
            vu_dist = d + cost
            if max_fees is not None:
                if vu_dist - value > max_fees:
                    continue
            if max_hops is not None:
                if n + 1 > max_hops:
                    continue
            if u in dist:
                if (n+1, vu_dist) < (dist_hop[u], dist[u]):
                    raise ValueError('Contradictory paths found:',
                                     'negative weights?')
            elif u not in seen or vu_dist < seen[u]:
                seen[u] = vu_dist
                push(fringe, (n+1, vu_dist, next(c), u))
                paths[u] = paths[v] + [u]
    try:
        return (dist[target]-value, paths[target])  # cost is the total fee, not the actual amount to be transfered
    except KeyError:
        raise nx.NetworkXNoPath(
            "node %s not reachable from %s" % (source, target))


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


def find_path_triangulation(G,
                            source,
                            target_reduce,
                            target_increase,
                            get_fee,
                            get_balance,
                            value,
                            max_hops=None,
                            max_fees=None):
    """
    target_reduce is the node we want to reduce our credit with
    target_increase is the node which will result with an increased debt
    source will owe less to target_reduce and target_increase will owe more to source
    must return a path and the total fee of that path
    to be called in the right order with source as source and target as target, contrary to find_path
    value must be >0
    """
    def get_fee_wrapper(a, b, value):
        # used to get the data from the graph in the right order and query the fees
        fee = get_fee(G[a][b], a, b, value)
        if fee is None:
            raise nx.NetworkXNoPath("node %s not reachable from %s" % (a, b))
        return fee

    # verification that the function is used properly
    if value <= 0:
        raise ValueError('This value cannot be handled yet : %d' % value)
    elif get_balance(G[target_reduce][source], target_reduce, source) < value:
        raise nx.NetworkXNoPath(
            f"The balance of target_reduce is lower than value {value}")

    G_adj = G.adj
    neighbors = [x[0] for x in G_adj[source].items()]

    if target_reduce not in neighbors:
        raise nx.NetworkXNoPath(
            "node %s not a neighbor of %s" % (target_reduce, source))
    if target_increase not in neighbors:
        raise nx.NetworkXNoPath(
            "node %s not a neighbor of %s" % (target_increase, source))
    if target_increase == target_reduce:
        raise ValueError("target_increase is equal target_reduce: %s" % target_increase)

    first_fee = get_fee_wrapper(target_reduce, source, value)

    if max_hops is not None:
        max_hops -= 2

    intermediary_fee, intermediary_path = find_path(G, target_reduce, target_increase,
                                                    get_fee, value+first_fee, max_hops, max_fees, source)

    last_fee = get_fee_wrapper(source, target_increase, value+intermediary_fee+first_fee)

    final_fee = last_fee + intermediary_fee + first_fee

    if max_fees is not None and final_fee > max_fees:
        raise nx.NetworkXNoPath(
            "operation impossible due to fees: %d with max_fees: %d" % (final_fee, max_fees))
    return (final_fee, list(reversed([source] + intermediary_path + [source])))


@attr.s(auto_attribs=True)
class PaymentPath:
    fee: int
    path: List
    value: int
    estimated_gas: int = attr.ib(default=None)


def find_possible_path_triangulations(G,
                                      source,
                                      target_reduce,
                                      get_fee,
                                      get_balance,
                                      value,
                                      max_hops=None,
                                      max_fees=None):
    """find ways to reduce sources' debt with it's neighbor target_reduce by value.

    source will have an increased debt to another neighbor
    This function returns a list of possible payment paths.
    """
    triangulations = []
    neighbors = {x[0] for x in G.adj[source].items()} - {target_reduce}
    for target_increase in neighbors:
        try:
            final_fee, path = find_path_triangulation(
                G,
                source,
                target_reduce,
                target_increase,
                get_fee,
                get_balance,
                value,
                max_hops=max_hops,
                max_fees=max_fees)
        except (nx.NetworkXNoPath, KeyError) as e:
            continue
        triangulations.append(PaymentPath(final_fee, path, value))
    return triangulations
