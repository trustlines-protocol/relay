import networkx as nx
from networkx.algorithms.shortest_paths.weighted import _dijkstra


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
