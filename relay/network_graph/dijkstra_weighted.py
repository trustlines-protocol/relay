from heapq import heappush, heappop
from itertools import count

import networkx as nx
import math

from .interests import balance_with_interest_estimation
from .graph_constants import *


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
            cost = get_fee(v, u, e, d)  # fee of transferring from u to v
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


def find_maximum_capacity_path(G, source, target, max_hops=None):
    """
    The logic is the same as dijkstra's Algorithm
    We visit nodes with the maximum capacity untill we reach the destination.
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

    def get_capacity(u, v, data):  # gets the capacity from u to v
        balance_with_interest = balance_with_interest_estimation(data)
        if (u < v):
            return data[creditline_ba] + balance_with_interest
        return data[creditline_ab] - balance_with_interest

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
                min_cap = min(capacity[u], get_capacity(u, v, e))
                if (v not in capacity) or (v in capacity and capacity[v] < min_cap):
                    capacity[v] = min_cap
                    paths[v] = paths[u]+[v]
                    push(fringe, (-capacity[v], next(c), v, n+1))

    try:
        capacities = []
        u = source

        for v in paths[target][1:]:
            if u < v:
                capacity = get_capacity(u, v, G[u][v])
            else:
                capacity = get_capacity(u, v, G[v][u])

            capacities.append(capacity)
            u = v

        return (seen[target], paths[target], capacities)
        # first element is the total capacity of the path not transferable amount
    except KeyError:
        raise nx.NetworkXNoPath(
            "node %s not reachable from %s" % (source, target))


def find_path_triangulation(G, source, target_reduce, target_increase, get_fee, value, max_hops=None, max_fees=None):
    """
    target_reduce is the node we want to reduce our credit with
    target_increase is the node which will result with an increased debt
    source will owe less to target_reduce and target_increase will owe more to source
    must return a path and the total fee of that path
    to be called in the right order with source as source and target as target, contrary to find_path
    value must be >0
    """
    def get_fee_wrapper(b, a, value):
        # used to get the data from the graph in the right order and query the fees
        if b < a:
            output = get_fee(b, a, G[b][a], value)
        else:
            output = get_fee(b, a, G[a][b], value)
        if output is None:
            raise nx.NetworkXNoPath("node %s not reachable from %s" % (a, b))
        return output

    def verify_balance_greater_than_value(a, b, value):
        # used to verify that we reduce the amount source owes to target_reduce and do not misuse the function
        if a < b:
            return -balance_with_interest_estimation(G[a][b]) >= value
        else:
            return balance_with_interest_estimation(G[b][a]) >= value

    # verification that the funtion is used properly
    if value <= 0:
        raise ValueError('This value cannot be handled yet : %d' % value)
    elif not verify_balance_greater_than_value(source, target_reduce, value):
        raise nx.NetworkXNoPath(
            "The balance of target_reduce is lower than value %d" % value)

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

    first_fee = get_fee_wrapper(source, target_reduce, value)

    if max_hops is not None:
        max_hops -= 2

    intermediary_fee, intermediary_path = find_path(G, target_reduce, target_increase,
                                                    get_fee, value+first_fee, max_hops, max_fees, source)

    last_fee = get_fee_wrapper(target_increase, source, value+intermediary_fee+first_fee)

    final_fee = last_fee + intermediary_fee + first_fee

    if max_fees is not None and final_fee > max_fees:
        raise nx.NetworkXNoPath(
            "operation impossible due to fees: %d with max_fees: %d" % (final_fee, max_fees))
    return (final_fee, list(reversed([source] + intermediary_path + [source])))
