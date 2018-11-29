from heapq import heappush, heappop
from itertools import count
from typing import List
import math

import networkx as nx
import attr


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
