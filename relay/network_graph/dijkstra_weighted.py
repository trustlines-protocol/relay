from heapq import heappush, heappop
from itertools import count

import networkx as nx


def _dijkstra(G, source, get_weight, pred=None, paths=None, cutoff=None,
              target=None):
    G_succ = G.succ if G.is_directed() else G.adj

    push = heappush
    pop = heappop
    dist = {}  # dictionary of final distances
    seen = {source: 0}
    c = count()
    fringe = []  # use heapq with (distance,label) tuples
    push(fringe, (0, next(c), source))
    while fringe:
        (d, _, v) = pop(fringe)
        if v in dist:
            continue  # already searched this node.
        dist[v] = d
        if v == target:
            break

        for u, e in G_succ[v].items():
            cost = get_weight(v, u, e)
            if cost is None:
                continue
            vu_dist = dist[v] + get_weight(v, u, e)
            if cutoff is not None:
                if vu_dist > cutoff:
                    continue
            if u in dist:
                if vu_dist < dist[u]:
                    raise ValueError('Contradictory paths found:',
                                     'negative weights?')
            elif u not in seen or vu_dist < seen[u]:
                seen[u] = vu_dist
                push(fringe, (vu_dist, next(c), u))
                if paths is not None:
                    paths[u] = paths[v] + [u]
                if pred is not None:
                    pred[u] = [v]
            elif vu_dist == seen[u]:
                if pred is not None:
                    pred[u].append(v)

    if paths is not None:
        return (dist, paths)
    if pred is not None:
        return (pred, dist)
    return dist


def dijkstra_path(G, source, target, get_weight):
    """Returns the shortest path from source to target in a weighted graph G"""
    (length, path) = single_source_dijkstra(G, source, target, get_weight)
    try:
        return path[target]
    except KeyError:
        raise nx.NetworkXNoPath(
            "node %s not reachable from %s" % (source, target))


def single_source_dijkstra(G, source, target, get_weight=None):
    """Compute shortest paths and lengths in a weighted graph G.    """
    if source == target:
        return ({source: 0}, {source: [source]})
    paths = {source: [source]}  # dictionary of paths
    return _dijkstra(G, source, get_weight, paths=paths, target=target)


def find_path(G, source, target, get_fee, value, max_hops=None, max_fees=None):
    G_succ = G.succ if G.is_directed() else G.adj

    paths = {source: [source]}  # dictionary of paths

    push = heappush
    pop = heappop
    dist = {}  # dictionary of final distances
    seen = {source: value}
    c = count()
    fringe = []  # use heapq with (distance,label) tuples
    push(fringe, (0, value, next(c), source))
    while fringe:
        (n, d, _, v) = pop(fringe)
        if v in dist:
            continue  # already searched this node.
        dist[v] = d
        if v == target:
            break

        for u, e in G_succ[v].items():
            cost = get_fee(v, u, e, d)
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
                if vu_dist < dist[u]:
                    raise ValueError('Contradictory paths found:',
                                     'negative weights?')
            elif u not in seen or vu_dist < seen[u]:
                seen[u] = vu_dist
                push(fringe, (n+1, vu_dist, next(c), u))
                paths[u] = paths[v] + [u]
    try:
        return (dist[target]-value, paths[target])
    except KeyError:
        raise nx.NetworkXNoPath(
            "node %s not reachable from %s" % (source, target))
