import tempfile
import logging
import time

import wrapt
from flask import request, send_file, make_response, abort
from flask.views import MethodView
from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate, fields as marshmallow_fields
from tldeploy import identity
from relay.utils import sha3
from relay.blockchain.currency_network_proxy import CurrencyNetworkProxy
from relay.blockchain.unw_eth_proxy import UnwEthProxy
from relay.blockchain.delegate import InvalidMetaTransactionException
from relay.api import fields as custom_fields
from .schemas import (
    CurrencyNetworkEventSchema,
    UserCurrencyNetworkEventSchema,
    AccountSummarySchema,
    TxInfosSchema,
    PaymentPathSchema,
    AnyEventSchema,
    TrustlineSchema,
    CurrencyNetworkSchema,
    MetaTransactionSchema,
)
from relay.relay import TrustlinesRelay
from relay.concurrency_utils import TimeoutException
from relay.logger import get_logger

from relay.network_graph.dijkstra_weighted import PaymentPath

logger = get_logger("api.resources", logging.DEBUG)


TIMEOUT_MESSAGE = "The server could not handle the request in time"


def abort_if_unknown_network(trustlines, network_address):
    if network_address not in trustlines.network_addresses:
        abort(404, "Unknown network: {}".format(network_address))


def dump_result_with_schema(schema):
    """returns a decorator that calls schema.dump on the functions or methods
    return value"""

    @wrapt.decorator
    def dump_result(wrapped, instance, args, kwargs):
        return schema.dump(wrapped(*args, **kwargs)).data

    return dump_result


class NetworkList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(CurrencyNetworkSchema(many=True))
    def get(self):
        return self.trustlines.get_network_infos()


class Network(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(CurrencyNetworkSchema())
    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.get_network_info(network_address)


class UserList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.get_users_of_network(network_address)


class User(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(AccountSummarySchema())
    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        return self.trustlines.currency_network_graphs[network_address].get_account_sum(
            user_address, timestamp=timestamp
        )


class ContactList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.currency_network_graphs[network_address].get_friends(
            user_address
        )


def _id(network_address, a_address, b_address):
    if a_address < b_address:
        return sha3(network_address + a_address + b_address)
    else:
        return sha3(network_address + b_address + a_address)


def _get_extended_account_summary(
    graph, network_address, a_address, b_address, timestamp: int
):
    account_summary = graph.get_account_sum(a_address, b_address, timestamp=timestamp)
    account_summary.user = a_address
    account_summary.counterParty = b_address
    account_summary.address = b_address
    account_summary.id = _id(network_address, a_address, b_address)
    return account_summary


class Trustline(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TrustlineSchema())
    def get(self, network_address, a_address, b_address):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]
        return _get_extended_account_summary(
            graph, network_address, a_address, b_address, timestamp=timestamp
        )


class TrustlineList(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TrustlineSchema(many=True))
    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]
        friends = graph.get_friends(user_address)
        return [
            _get_extended_account_summary(
                graph,
                network_address,
                user_address,
                friend_address,
                timestamp=timestamp,
            )
            for friend_address in friends
        ]


class MaxCapacityPath(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "maxHops": fields.Int(required=False, missing=None),
        "from": custom_fields.Address(required=True),
        "to": custom_fields.Address(required=True),
    }

    @use_args(args)
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)

        source = args["from"]
        target = args["to"]
        max_hops = args["maxHops"]

        timestamp = int(time.time())

        capacity, path = self.trustlines.currency_network_graphs[
            network_address
        ].find_maximum_capacity_path(
            source=source, target=target, max_hops=max_hops, timestamp=timestamp
        )

        return {"capacity": str(capacity), "path": path}


class UserEventsNetwork(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(CurrencyNetworkProxy.event_types),
            missing=None,
        ),
    }

    @use_args(args)
    @dump_result_with_schema(UserCurrencyNetworkEventSchema(many=True))
    def get(self, args, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args["fromBlock"]
        type = args["type"]
        try:

            return self.trustlines.get_user_network_events(
                network_address, user_address, type=type, from_block=from_block
            )
        except TimeoutException:
            logger.warning(
                "User network events: event_name=%s user_address=%s from_block=%s. could not get events in time",
                type,
                user_address,
                from_block,
            )
            abort(504, TIMEOUT_MESSAGE)


class UserEvents(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(
                CurrencyNetworkProxy.event_types + UnwEthProxy.event_types
            ),
            missing=None,
        ),
    }

    @use_args(args)
    @dump_result_with_schema(AnyEventSchema(many=True))
    def get(self, args, user_address: str):
        type = args["type"]
        from_block = args["fromBlock"]
        try:
            return self.trustlines.get_user_events(
                user_address,
                type=type,
                from_block=from_block,
                timeout=self.trustlines.event_query_timeout,
            )
        except TimeoutException:
            logger.warning(
                "User events: event_name=%s user_address=%s from_block=%s. could not get events in time",
                type,
                user_address,
                from_block,
            )
            abort(504, TIMEOUT_MESSAGE)


class EventsNetwork(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "fromBlock": fields.Int(required=False, missing=0),
        "type": fields.Str(
            required=False,
            validate=validate.OneOf(CurrencyNetworkProxy.event_types),
            missing=None,
        ),
    }

    @use_args(args)
    @dump_result_with_schema(CurrencyNetworkEventSchema(many=True))
    def get(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args["fromBlock"]
        type = args["type"]
        try:
            return self.trustlines.get_network_events(
                network_address, type=type, from_block=from_block
            )
        except TimeoutException:
            logger.warning(
                "Network events: event_name=%s from_block=%s. could not get events in time",
                type,
                from_block,
            )
            abort(504, TIMEOUT_MESSAGE)


class TransactionInfos(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    @dump_result_with_schema(TxInfosSchema())
    def get(self, user_address: str):
        return self.trustlines.node.get_tx_infos(user_address)


class Relay(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {"rawTransaction": fields.String(required=True)}

    @use_args(args)
    def post(self, args):
        try:
            return self.trustlines.node.relay_tx(args["rawTransaction"]).hex()
        except ValueError:  # should mean error in relaying the transaction
            abort(409, "There was an error while relaying this transaction")


class RelayMetaTransaction(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "metaTransaction": marshmallow_fields.Nested(
            MetaTransactionSchema, required=True
        )
    }

    @use_args(args)
    def post(self, args):
        meta_transaction: identity.MetaTransaction = args["metaTransaction"]
        try:
            return self.trustlines.delegate_metatransaction(meta_transaction).hex()
        except InvalidMetaTransactionException:
            abort(400, "The meta-transaction is invalid")
        except ValueError:
            abort(409, "There was an error while relaying this meta-transaction")


class Balance(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, user_address: str):
        return str(self.trustlines.node.balance(user_address))


class Block(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.node.blocknumber


class RequestEther(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def post(self):
        address = request.json["address"]
        return self.trustlines.node.send_ether(address)


class DeployIdentity(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {"ownerAddress": custom_fields.Address(required=True)}

    @use_args(args)
    def post(self, args):
        owner_address = args["ownerAddress"]
        identity_contract = self.trustlines.deploy_identity(owner_address)
        # we may like to return additonal fields here in the future, therefore
        # the return value is a map
        return {"identity": identity_contract.address}


def _estimate_gas_for_transfer(
    trustlines: TrustlinesRelay, payment_path: PaymentPath, network_address: str
) -> PaymentPath:
    proxy = trustlines.currency_network_proxies[network_address]
    try:
        payment_path.estimated_gas = proxy.estimate_gas_for_payment_path(payment_path)
    except ValueError:  # should mean out of gas, so path was not right.
        return PaymentPath(fee=0, path=[], value=payment_path.value, estimated_gas=0)

    return payment_path


class Path(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "value": fields.Int(required=False, missing=1, validate=validate.Range(min=1)),
        "maxHops": fields.Int(required=False, missing=None),
        "maxFees": fields.Int(required=False, missing=None),
        "from": custom_fields.Address(required=True),
        "to": custom_fields.Address(required=True),
    }

    @use_args(args)
    @dump_result_with_schema(PaymentPathSchema())
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        timestamp = int(time.time())

        source = args["from"]
        target = args["to"]
        value = args["value"]
        max_fees = args["maxFees"]
        max_hops = args["maxHops"]

        cost, path = self.trustlines.currency_network_graphs[network_address].find_path(
            source=source,
            target=target,
            value=value,
            max_fees=max_fees,
            max_hops=max_hops,
            timestamp=timestamp,
        )

        return _estimate_gas_for_transfer(
            self.trustlines, PaymentPath(cost, path, value), network_address
        )


# CloseTrustline is similar to the above ReduceDebtPath, though it does not
# take `via` and `value` as parameters. Instead it tries to reduce the debt to
# zero and uses any contact to do so.


class CloseTrustline(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "maxHops": fields.Int(required=False, missing=None),
        "maxFees": fields.Int(required=False, missing=None),
        "from": custom_fields.Address(required=True),
        "to": custom_fields.Address(required=True),
    }

    @use_args(args)
    @dump_result_with_schema(PaymentPathSchema())
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        source = args["from"]
        target = args["to"]
        max_fees = args["maxFees"]
        max_hops = args["maxHops"]

        now = int(time.time())
        graph = self.trustlines.currency_network_graphs[network_address]

        payment_path = graph.close_trustline_path_triangulation(
            timestamp=now,
            source=source,
            target=target,
            max_hops=max_hops,
            max_fees=max_fees,
        )

        proxy = self.trustlines.currency_network_proxies[network_address]
        try:
            payment_path.estimated_gas = proxy.estimate_gas_for_close_trustline(
                source=source,
                other_party=target,
                max_fee=max_fees or 2 ** 32 - 1,
                path=payment_path.path,
            )
        except ValueError:  # should mean out of gas, so path was not right.
            return PaymentPath(
                fee=0, path=[], value=payment_path.value, estimated_gas=0
            )

        return payment_path


class GraphImage(MethodView):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        filename = tempfile.mktemp(".gif")
        self.trustlines.currency_network_graphs[network_address].draw(filename)
        return send_file(filename, mimetype="image/gif")


class GraphDump(MethodView):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        response = make_response(
            self.trustlines.currency_network_graphs[network_address].dump()
        )
        cd = "attachment; filename=networkdump.csv"
        response.headers["Content-Disposition"] = cd
        response.mimetype = "text/csv"
        return response
