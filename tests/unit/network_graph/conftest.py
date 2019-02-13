import pytest

from relay.blockchain.currency_network_proxy import Trustline
from relay.network_graph.graph import (
    CurrencyNetworkGraphForTesting as CurrencyNetworkGraph,
)

addresses = ["0x0A", "0x0B", "0x0C", "0x0D", "0x0E", "0x0F", "0x10", "0x11"]
A, B, C, D, E, F, G, H = addresses


@pytest.fixture
def trustlines():
    return [
        Trustline(A, B, 100, 150),
        Trustline(A, E, 500, 550),
        Trustline(B, C, 200, 250),
        Trustline(C, D, 300, 350),
        Trustline(D, E, 400, 450),
    ]


@pytest.fixture
def community_with_trustlines(trustlines):
    community = CurrencyNetworkGraph()
    community.gen_network(trustlines)
    return community


@pytest.fixture
def community_with_trustlines_and_fees(trustlines):
    community = CurrencyNetworkGraph(100)
    community.gen_network(trustlines)
    return community


@pytest.fixture()
def configurable_community(request):
    """Graph fixture that can be configures with a NetworkGraphConfig"""
    community = CurrencyNetworkGraph.from_config(request.param)
    return community
