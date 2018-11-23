"""graph algorithms"""

import heapq
from typing import List, Set, Dict, Callable
import networkx as nx
import abc


class CostAccumulator(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def zero(self):
        """return 'zero cost' element, which is the initial cost for a one-node path

        This must be less than or equal to any value
        accumulate_cost_for_next_hop returns.
        """
        pass

    @abc.abstractmethod
    def accumulate_cost_for_next_hop(
        self, cost_from_start_to_node, node, dst, graph_data
    ):
        """
        compute the total cost from one of the starting nodes to dst via node
        given that the cost from one of the starting nodes to node is
        cost_from_start_to_node.

        In other words this adds the cost for the hop from node to dst to
        cost_from_start_to_node

        This function must return a value greater or equal to the given
        cost_from_start_to_node parameter.
        """
        pass

    def compute_cost_for_path(self, graph, path):
        cost = self.zero()
        for source, dst in zip(path, path[1:]):
            cost = self.accumulate_cost_for_next_hop(
                cost, source, dst, graph.get_edge_data(source, dst)
            )
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

    while queue:
        cost_from_start_to_node, node = heapq.heappop(queue)
        if node in target_nodes:
            return cost_from_start_to_node, _build_path_from_backlinks(node, backlinks)

        if cost_from_start_to_node > least_costs[node]:
            continue  # we already found a cheaper path to node

        for dst, edge_data in graph_adj[node].items():
            cost_from_start_to_dst = cost_fn(
                cost_from_start_to_node, node, dst, edge_data
            )
            if cost_from_start_to_dst is None:
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
    graph,
    starting_nodes,
    target_nodes: Set,
    cost_accumulator: CostAccumulator,
    max_cost=None,
):
    """find the path through the given graph with least cost from one of the
    starting_nodes to one of the target_nodes

    cost_accumulator is used to compute the cost
    """
    zero_cost = cost_accumulator.zero()
    cost_fn = cost_accumulator.accumulate_cost_for_next_hop
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
