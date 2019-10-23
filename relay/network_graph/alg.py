"""graph algorithms"""

import abc
import heapq
from typing import Callable, Dict, Iterable, List, Set

import networkx as nx


class CostAccumulator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def zero(self):
        """return 'zero cost' element, which is the initial cost for a one-node path

        This must be less than or equal to any value
        total_cost_from_start_to_dst returns.
        """
        pass

    @abc.abstractmethod
    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node, node, dst, edge_data
    ):
        """
        compute the total cost from one of the starting nodes to dst via node
        given that the cost from one of the starting nodes to node is the given parameter
        cost_from_start_to_node.

        In other words this adds the cost for the hop from node to dst to
        cost_from_start_to_node.

        edge_data is the data that's stored inside the graph for the edge from
        node to dst.

        This function must return a value greater or equal to the given
        cost_from_start_to_node parameter when used with the least_cost_path
        function below, since that implement dijkstra's graph finding
        algorithm, where negative weights are not allowed.

        It may also return None, which means that this path - from one of the
        starting nodes, to node, to dst - is forbidden.
        """
        pass

    def compute_cost_for_path(self, graph: nx.graph.Graph, path: List):
        """
        compute the cost for the given path. This may raise nx.NetworkXNoPath if
        total_cost_from_start_to_dst returns None. E.g. if the CostAccumulator
        has limits on the fees or maximum number of hops this may return None"""
        cost = self.zero()
        for source, dst in zip(path, path[1:]):
            cost = self.total_cost_from_start_to_dst(
                cost, source, dst, graph.get_edge_data(source, dst)
            )
            if cost is None:
                raise nx.NetworkXNoPath("no path found")
        return cost


def _build_path_from_backlinks(dst: List, backlinks: Dict):
    path = [dst]
    while True:
        dst = backlinks[dst]
        if dst is None:
            path.reverse()
            return path
        path.append(dst)


def _least_cost_path_helper(
    graph: nx.graph.Graph,
    target_nodes: Set,
    queue: List,
    least_costs: Dict,
    backlinks: Dict,
    cost_fn: Callable,
    max_cost=None
    #    node_filter,
    #    edge_filter,
):
    graph_adj = graph.adj

    visited_nodes = set()  # set of nodes, where we already found the minimal path
    while queue:
        cost_from_start_to_node, node = heapq.heappop(queue)
        if node in target_nodes:
            return cost_from_start_to_node, _build_path_from_backlinks(node, backlinks)

        if cost_from_start_to_node > least_costs[node]:
            continue  # we already found a cheaper path to node

        visited_nodes.add(node)
        for dst, edge_data in graph_adj[node].items():
            if dst in visited_nodes:
                continue
            cost_from_start_to_dst = cost_fn(
                cost_from_start_to_node, node, dst, edge_data
            )
            if cost_from_start_to_dst is None:  # cost_fn decided this path is forbidden
                continue

            if max_cost is not None and max_cost < cost_from_start_to_dst:
                continue

            assert cost_from_start_to_dst >= cost_from_start_to_node

            least_cost_found_so_far_from_start_to_dst = least_costs.get(dst)
            if (
                least_cost_found_so_far_from_start_to_dst is None
                or cost_from_start_to_dst < least_cost_found_so_far_from_start_to_dst
            ):
                heapq.heappush(queue, (cost_from_start_to_dst, dst))
                least_costs[dst] = cost_from_start_to_dst
                backlinks[dst] = node

    raise nx.NetworkXNoPath("no path found")


def least_cost_path(
    *,
    graph: nx.graph.Graph,
    starting_nodes: Iterable,
    target_nodes: Set,
    cost_accumulator: CostAccumulator,
    max_cost=None,
):
    """find the path through the given graph with least cost from one of the
    starting_nodes to one of the target_nodes

    cost_accumulator is used to compute the cost

    When max_cost is given, only return a path, whose cost is smaller than
    max_cost.

    This is an implementation of dijkstra's multi-source multi-target path
    finding algorithm. As a result the given cost_accumulator's
    total_cost_from_start_to_dst function must return a value that's equal or
    greater than it's given cost_from_start_to_node parameter, i.e. it must not
    use 'negative costs'.
    """
    zero_cost = cost_accumulator.zero()
    cost_fn = cost_accumulator.total_cost_from_start_to_dst
    assert max_cost is None or zero_cost <= max_cost

    least_costs: Dict = {}
    backlinks: Dict = {}
    queue: List = []
    for node in starting_nodes:
        if not graph.has_node(node):
            continue
        least_costs[node] = zero_cost
        backlinks[node] = None
        heapq.heappush(queue, (zero_cost, node))

    return _least_cost_path_helper(
        graph, target_nodes, queue, least_costs, backlinks, cost_fn, max_cost=max_cost
    )
