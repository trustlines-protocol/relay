from flask import Flask, Blueprint
from flask_restful import Api
from werkzeug.routing import BaseConverter, ValidationError

from relay.resources import User, UserList, Network, NetworkList, ContactList, TrustlineList, Trustline, Relay, Balance, TransactionInfos, Block
from relay.utils import is_address, add_0x_prefix

class AddressConverter(BaseConverter):

    def to_python(self, value):
        if not is_address(value):
            raise ValidationError()
        value = add_0x_prefix(value)
        return value

    def to_url(self, value):
        if not is_address(value):
            raise ValueError("Not a valid address")
        return add_0x_prefix(value)


def ApiApp(trustlines):
    app = Flask(__name__)
    api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
    api = Api(api_bp)

    api.add_resource(NetworkList, '/networks', resource_class_args=[trustlines])
    api.add_resource(Network, '/networks/<address:address>', resource_class_args=[trustlines])
    api.add_resource(UserList, '/networks/<address:address>/users', resource_class_args=[trustlines])
    api.add_resource(User, '/networks/<address:network_address>/users/<address:user_address>', resource_class_args=[trustlines])
    api.add_resource(ContactList, '/networks/<address:network_address>/users/<address:user_address>/contacts', resource_class_args=[trustlines])
    api.add_resource(TrustlineList, '/networks/<address:network_address>/users/<address:user_address>/trustlines', resource_class_args=[trustlines])
    api.add_resource(Trustline, '/networks/<address:network_address>/users/<address:a_address>/trustlines/<address:b_address>', resource_class_args=[trustlines])
    api.add_resource(Block, '/blocknumber', resource_class_args=[trustlines])
    api.add_resource(Balance, '/balance/<address:address>', resource_class_args=[trustlines])

    app.url_map.converters['address'] = AddressConverter
    app.register_blueprint(api_bp)

    return app
