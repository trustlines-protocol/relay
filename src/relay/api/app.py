from enum import Enum, auto

from eth_utils import is_address, is_checksum_address, to_checksum_address
from flask import Blueprint, Flask, jsonify
from flask_cors import CORS
from flask_restful import Api
from flask_sockets import Sockets
from webargs.flaskparser import abort, parser
from werkzeug.exceptions import HTTPException
from werkzeug.routing import BaseConverter, ValidationError

from .exchange.resources import (
    EventsExchange,
    ExchangeAddresses,
    OrderBook,
    OrderDetail,
    Orders,
    OrderSubmission,
    UnwEthAddresses,
    UserEventsAllExchanges,
    UserEventsExchange,
)
from .messaging.resources import PostMessage
from .pushservice.resources import AddClientToken, DeleteClientToken
from .resources import (
    Balance,
    Block,
    CloseTrustline,
    ContactList,
    DeployIdentity,
    EventsNetwork,
    Factories,
    GraphDump,
    GraphImage,
    IdentityInfos,
    MaxCapacityPath,
    MetaTransactionFees,
    Network,
    NetworkList,
    Path,
    Relay,
    RelayMetaTransaction,
    RequestEther,
    TransactionInfos,
    Trustline,
    TrustlineAccruedInterestList,
    TrustlineList,
    User,
    UserAccruedInterestList,
    UserEvents,
    UserEventsNetwork,
    UserList,
    UserTrustlines,
    Version,
)
from .streams.app import MessagingWebSocketRPCHandler, WebSocketRPCHandler
from .tokens.resources import EventsToken, TokenAddresses, TokenBalance, UserEventsToken


class ApiType(Enum):
    FAUCET = auto()
    DELEGATE = auto()
    PATHFINDING = auto()
    STATUS = auto()
    EXCHANGE = auto()
    RELAY = auto()
    MESSAGING = auto()
    PUSH_NOTIFICATION = auto()


class AddressConverter(BaseConverter):
    def to_python(self, value):
        if not is_address(value):
            raise ValidationError()
        return to_checksum_address(value)

    def to_url(self, value):
        if not is_checksum_address(value):
            raise ValueError("Not a valid checksum address")
        return


def ApiApp(trustlines, *, enabled_apis):
    app = Flask(__name__)
    app.register_error_handler(Exception, handle_error)
    sockets = Sockets(app)
    Api(app, catch_all_404s=True)
    CORS(app, send_wildcard=True)
    api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
    sockets_bp = Blueprint("api", __name__, url_prefix="/api/v1/streams")
    api = Api(api_bp)

    def add_resource(resource, url):
        api.add_resource(resource, url, resource_class_args=[trustlines])

    # Always enabled
    api.add_resource(Version, "/version")
    add_resource(Block, "/blocknumber")

    if ApiType.STATUS in enabled_apis:
        add_resource(NetworkList, "/networks")
        add_resource(Network, "/networks/<address:network_address>")
        add_resource(UserList, "/networks/<address:network_address>/users")
        add_resource(EventsNetwork, "/networks/<address:network_address>/events")
        add_resource(
            UserAccruedInterestList,
            "/networks/<address:network_address>/users/<address:user_address>/interests",
        )
        add_resource(
            TrustlineAccruedInterestList,
            "/networks/<address:network_address>/users/<address:user_address>/"
            "interests/<address:counterparty_address>",
        )
        add_resource(
            User, "/networks/<address:network_address>/users/<address:user_address>"
        )
        add_resource(
            ContactList,
            "/networks/<address:network_address>/users/<address:user_address>/contacts",
        )
        add_resource(
            TrustlineList,
            "/networks/<address:network_address>/users/<address:user_address>/trustlines",
        )
        add_resource(
            Trustline,
            "/networks/<address:network_address>/users/<address:a_address>/trustlines/<address:b_address>",
        )
        add_resource(
            UserEventsNetwork,
            "/networks/<address:network_address>/users/<address:user_address>/events",
        )
        add_resource(UserEvents, "/users/<address:user_address>/events")
        add_resource(TransactionInfos, "/users/<address:user_address>/txinfos")
        add_resource(Balance, "/users/<address:user_address>/balance")
        add_resource(UserTrustlines, "/users/<address:user_address>/trustlines")

        api_bp.add_url_rule(
            "/networks/<address:network_address>/image",
            view_func=GraphImage.as_view("image", trustlines),
        )
        api_bp.add_url_rule(
            "/networks/<address:network_address>/dump",
            view_func=GraphDump.as_view("dump", trustlines),
        )

        sockets_bp.add_url_rule(
            "/events", "stream", view_func=WebSocketRPCHandler(trustlines)
        )

    if ApiType.PATHFINDING in enabled_apis:
        add_resource(
            MaxCapacityPath,
            "/networks/<address:network_address>/max-capacity-path-info",
        )
        add_resource(Path, "/networks/<address:network_address>/path-info")
        add_resource(
            CloseTrustline,
            "/networks/<address:network_address>/close-trustline-path-info",
        )

    if ApiType.RELAY in enabled_apis:
        add_resource(Relay, "/relay")

    if ApiType.DELEGATE in enabled_apis:
        add_resource(RelayMetaTransaction, "/relay-meta-transaction")
        add_resource(MetaTransactionFees, "/meta-transaction-fees")
        add_resource(IdentityInfos, "/identities/<address:identity_address>")
        add_resource(Factories, "/factories")
        if trustlines.enable_deploy_identity:
            add_resource(DeployIdentity, "/identities")

    if ApiType.FAUCET in enabled_apis:
        add_resource(RequestEther, "/request-ether")

    if ApiType.EXCHANGE in enabled_apis:
        add_resource(OrderBook, "/exchange/orderbook")
        add_resource(Orders, "/exchange/orders")
        add_resource(OrderSubmission, "/exchange/order")
        add_resource(ExchangeAddresses, "/exchange/exchanges")
        add_resource(UnwEthAddresses, "/exchange/eth")
        add_resource(OrderDetail, "/exchange/order/<string:order_hash>")
        add_resource(
            UserEventsExchange,
            "/exchange/<address:exchange_address>/users/<address:user_address>/events",
        )
        add_resource(
            UserEventsAllExchanges, "/exchange/users/<address:user_address>/events"
        )
        add_resource(EventsExchange, "/exchange/<address:exchange_address>/events")

        add_resource(TokenAddresses, "/tokens")
        add_resource(EventsToken, "/tokens/<address:token_address>/events")
        add_resource(
            TokenBalance,
            "/tokens/<address:token_address>/users/<address:user_address>/balance",
        )
        add_resource(
            UserEventsToken,
            "/tokens/<address:token_address>/users/<address:user_address>/events",
        )

    if ApiType.MESSAGING in enabled_apis:
        add_resource(PostMessage, "/messages/<address:user_address>")
        sockets_bp.add_url_rule(
            "/messages", "stream", view_func=MessagingWebSocketRPCHandler(trustlines)
        )

    if ApiType.PUSH_NOTIFICATION in enabled_apis:
        add_resource(
            AddClientToken,
            "/pushnotifications/<address:user_address>/token/<string:client_token>",
        )
        add_resource(
            DeleteClientToken,
            "/pushnotifications/<address:user_address>/token/<string:client_token>",
        )

    app.url_map.converters["address"] = AddressConverter
    app.register_blueprint(api_bp)
    sockets.register_blueprint(sockets_bp)

    return app


# This error handler is necessary for usage with Flask-RESTful
@parser.error_handler
def handle_request_parsing_error(err, req, schema, status_code, headers):
    """webargs error handler that uses Flask-RESTful's abort function to return
    a JSON error response to the client.
    """
    message = ", ".join(
        f"{field}: {', '.join(messages)}" for field, messages in err.messages.items()
    )
    abort(
        422, message=f"Validation errors in your request: {message}", error=err.messages
    )


# Handle all errors as json
def handle_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return (
        jsonify(
            message="The server encountered an internal error and was unable to complete your request.  "
            "Either the server is overloaded or there is an error in the application."
        ),
        code,
    )
