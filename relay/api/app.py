from flask import Flask, Blueprint
from flask_cors import CORS
from flask_restful import Api
from webargs.flaskparser import parser, abort
from werkzeug.routing import BaseConverter, ValidationError
from eth_utils import is_address, to_checksum_address, is_checksum_address

from .resources import GraphDump, GraphImage, RequestEther, User, UserList, Network, NetworkList, \
    ContactList, TrustlineList, Trustline, Spendable, SpendableTo, Path, UserEventsNetwork, UserEvents, Relay, \
    Balance, TransactionInfos, Block, EventsNetwork
from .exchange.resources import OrderBook, OrderSubmission, ExchangeAddresses, UnwEthAddresses


class AddressConverter(BaseConverter):

    def to_python(self, value):
        if not is_address(value):
            raise ValidationError()
        return to_checksum_address(value)

    def to_url(self, value):
        if not is_checksum_address(value):
            raise ValueError("Not a valid checksum address")
        return


def ApiApp(trustlines):
    app = Flask(__name__)
    Api(app, catch_all_404s=True)
    CORS(app)
    api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
    api = Api(api_bp)

    def add_resource(resource, url):
        api.add_resource(resource, url, resource_class_args=[trustlines])

    add_resource(NetworkList, '/networks')
    add_resource(Network, '/networks/<address:network_address>')
    add_resource(UserList, '/networks/<address:network_address>/users')
    add_resource(EventsNetwork, '/networks/<address:network_address>/events')
    add_resource(User, '/networks/<address:network_address>/users/<address:user_address>')
    add_resource(ContactList, '/networks/<address:network_address>/users/<address:user_address>/contacts')
    add_resource(TrustlineList, '/networks/<address:network_address>/users/<address:user_address>/trustlines')
    add_resource(Trustline,
                 '/networks/<address:network_address>/users/<address:a_address>/trustlines/<address:b_address>')
    add_resource(Spendable, '/networks/<address:network_address>/users/<address:a_address>/spendable')
    add_resource(SpendableTo,
                 '/networks/<address:network_address>/users/<address:a_address>/spendables/<address:b_address>')
    add_resource(UserEventsNetwork, '/networks/<address:network_address>/users/<address:user_address>/events')
    add_resource(Path, '/networks/<address:network_address>/path-info')

    add_resource(UserEvents, '/users/<address:user_address>/events')
    add_resource(TransactionInfos, '/users/<address:user_address>/txinfos')
    add_resource(Balance, '/users/<address:user_address>/balance')

    add_resource(Block, '/blocknumber')
    add_resource(Relay, '/relay')
    add_resource(RequestEther, '/request-ether')

    add_resource(OrderBook, '/exchange/orderbook')
    add_resource(OrderSubmission, '/exchange/order')
    add_resource(ExchangeAddresses, '/exchange/exchanges')
    add_resource(UnwEthAddresses, '/exchange/eth')

    api_bp.add_url_rule('/networks/<address:address>/image', view_func=GraphImage.as_view('image', trustlines))
    api_bp.add_url_rule('/networks/<address:address>/dump', view_func=GraphDump.as_view('dump', trustlines))

    app.url_map.converters['address'] = AddressConverter
    app.register_blueprint(api_bp)

    return app


# This error handler is necessary for usage with Flask-RESTful
@parser.error_handler
def handle_request_parsing_error(err):
    """webargs error handler that uses Flask-RESTful's abort function to return
    a JSON error response to the client.
    """
    abort(422, message='Validation errors in your request', error=err.messages)
