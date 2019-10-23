import networkx as nx

from relay.network_graph import alg


class FeeCostAccumulatorCounter(alg.CostAccumulator):
    def __init__(self):
        self.num_calls = 0

    def zero(self):
        return 0

    def total_cost_from_start_to_dst(
        self, cost_from_start_to_node, node, dst, graph_data
    ):
        self.num_calls += 1
        return cost_from_start_to_node + graph_data["fee"]


def test_optimize_number_of_costfn_calls():
    """test that least_cost_path does not call costfn excessively

    see https://github.com/trustlines-protocol/relay/issues/237
    """
    g = nx.Graph()
    nodes = list(range(1, 20))
    for src, dst in zip(nodes, nodes[1:]):
        g.add_edge(src, dst, fee=1)

    cost_accumulator = FeeCostAccumulatorCounter()
    alg.least_cost_path(
        graph=g,
        starting_nodes={nodes[0]},
        target_nodes={nodes[-1]},
        cost_accumulator=cost_accumulator,
    )
    assert cost_accumulator.num_calls == len(nodes) - 1
