from flask_restful import Resource
from webargs.flaskparser import use_args
from webargs import fields as webfields
from webargs.flaskparser import abort
from eth_utils import to_checksum_address

from relay.relay import TrustlinesRelay
from relay.api import fields
from relay.exchange.order import Order
from relay.exchange.orderbook import OrderInvalidException

class TokenAddresses(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.unw_eth


