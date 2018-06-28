from heapq import heappush, heappop
from itertools import count

import networkx as nx


def find_path(G, source, target, get_fee, value, max_hops=None, max_fees=None, ignore=None):
    G_succ = G.succ if G.is_directed() else G.adj

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

        for u, e in G_succ[v].items():
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
            return -G[a][b]['balance_ab'] >= value
        else:
            return G[b][a]['balance_ab'] >= value

    # verification that the funtion is used properly
    if value <= 0:
        raise ValueError('This value cannot be handled yet : %d' % value)
    elif not verify_balance_greater_than_value(source, target_reduce, value):
        raise nx.NetworkXNoPath(
            "The balance of target_reduce is lower than value %d" % value)

    G_succ = G.succ if G.is_directed() else G.adj
    neighbors = [x[0] for x in G_succ[source].items()]

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
