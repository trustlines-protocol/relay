import tempfile
import logging

import wrapt
from flask import request, send_file, make_response, abort
from flask.views import MethodView
from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate

from relay.utils import sha3
from relay.blockchain.currency_network_proxy import CurrencyNetworkProxy
from relay.blockchain.unw_eth_proxy import UnwEthProxy
from relay.blockchain.unw_eth_events import UnwEthEvent
from relay.blockchain.exchange_events import ExchangeEvent
from relay.blockchain.currency_network_events import CurrencyNetworkEvent
from relay.api import fields as custom_fields
from .schemas import (CurrencyNetworkEventSchema,
                      UserCurrencyNetworkEventSchema,
                      UserTokenEventSchema,
                      ExchangeEventSchema,
                      AccountSummarySchema,
                      TrustlineSchema,
                      TxInfosSchema,
                      CloseTrustlineResultSchema)
from relay.relay import TrustlinesRelay
from relay.concurrency_utils import TimeoutException
from relay.logger import get_logger

from relay.network_graph.dijkstra_weighted import PaymentPath

logger = get_logger('apiresources', logging.DEBUG)


TIMEOUT_MESSAGE = 'The server could not handle the request in time'


def abort_if_unknown_network(trustlines, network_address):
    if network_address not in trustlines.networks:
        abort(404, 'Unknown network: {}'.format(network_address))


def dump_result_with_schema(schema):
    """returns a decorator that calls schema.dump on the functions or methods
    return value"""
    @wrapt.decorator
    def dump_result(wrapped, instance, args, kwargs):
        result = schema.dump(wrapped(*args, **kwargs)).data
        # schema.validate(result)
        return result
    return dump_result


class NetworkList(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self):
        result = []
        for address in self.trustlines.networks:
            result.append({
                'address': address,
                'name': self.trustlines.currency_network_proxies[address].name,
                'abbreviation': self.trustlines.currency_network_proxies[address].symbol,
            })
        return result


class Network(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return {
            'address': network_address,
            'name': self.trustlines.currency_network_proxies[network_address].name,
            'abbreviation': self.trustlines.currency_network_proxies[network_address].symbol,
            'decimals': self.trustlines.currency_network_proxies[network_address].decimals,
            'numUsers': len(self.trustlines.currency_network_graphs[network_address].users)
        }


class UserList(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.currency_network_proxies[network_address].users


class User(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return AccountSummarySchema().dump(
            self.trustlines.currency_network_graphs[network_address].get_account_sum(user_address)).data


class ContactList(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.currency_network_graphs[network_address].get_friends(user_address)


def _id(network_address, a_address, b_address):
        if a_address < b_address:
            return sha3(network_address + a_address + b_address)
        else:
            return sha3(network_address + b_address + a_address)


class Trustline(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        abort_if_unknown_network(self.trustlines, network_address)
        graph = self.trustlines.currency_network_graphs[network_address]
        data = TrustlineSchema().dump(graph.get_account_sum(a_address, b_address)).data
        data.update({
            'user': a_address,
            'counterParty': b_address,
            'address': b_address,
            'id': _id(network_address, a_address, b_address)
        })
        return data


class TrustlineList(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        graph = self.trustlines.currency_network_graphs[network_address]
        friends = graph.get_friends(user_address)
        accounts = []
        for friend_address in friends:
            data = TrustlineSchema().dump(graph.get_account_sum(user_address, friend_address)).data
            data.update(
                {
                    'user': user_address,
                    'counterParty': friend_address,
                    'address': friend_address,
                    'id': _id(network_address, user_address, friend_address)
                }
            )
            accounts.append(data)
        return accounts


class MaxCapacityPath(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'maxHops': fields.Int(required=False, missing=None),
        'from': custom_fields.Address(required=True),
        'to': custom_fields.Address(required=True)
    }

    @use_args(args)
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)

        source = args['from']
        target = args['to']
        max_hops = args['maxHops']

        capacity, path = self.trustlines.currency_network_graphs[network_address].find_maximum_capacity_path(
            source=source,
            target=target,
            max_hops=max_hops)

        return {'capacity': str(capacity),
                'path': path}


class UserEventsNetwork(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetworkProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args['fromBlock']
        type = args['type']
        try:
            events = self.trustlines.get_user_network_events(network_address,
                                                             user_address,
                                                             type=type,
                                                             from_block=from_block)
        except TimeoutException:
            logger.warning(
                "User network events: event_name=%s user_address=%s from_block=%s. could not get events in time",
                type,
                user_address,
                from_block)
            abort(504, TIMEOUT_MESSAGE)
        return UserCurrencyNetworkEventSchema().dump(events, many=True).data


class UserEvents(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetworkProxy.event_types +
                                                   UnwEthProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, user_address: str):
        type = args['type']
        from_block = args['fromBlock']
        try:
            events = self.trustlines.get_user_events(user_address,
                                                     type=type,
                                                     from_block=from_block,
                                                     timeout=self.trustlines.event_query_timeout)
        except TimeoutException:
            logger.warning(
                "User events: event_name=%s user_address=%s from_block=%s. could not get events in time",
                type,
                user_address,
                from_block)
            abort(504, TIMEOUT_MESSAGE)
        serialized_events = []
        for event in events:
            if isinstance(event, CurrencyNetworkEvent):
                serialized_events.append(UserCurrencyNetworkEventSchema().dump(event).data)
            if isinstance(event, UnwEthEvent):
                serialized_events.append(UserTokenEventSchema().dump(event).data)
            if isinstance(event, ExchangeEvent):
                serialized_events.append(ExchangeEventSchema().dump(event).data)
        return serialized_events


class EventsNetwork(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetworkProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        from_block = args['fromBlock']
        type = args['type']
        try:
            events = self.trustlines.get_network_events(network_address, type=type, from_block=from_block)
        except TimeoutException:
            logger.warning(
                "Network events: event_name=%s from_block=%s. could not get events in time",
                type,
                from_block)
            abort(504, TIMEOUT_MESSAGE)
        return CurrencyNetworkEventSchema().dump(events, many=True).data


class TransactionInfos(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, user_address: str):
        return TxInfosSchema().dump(self.trustlines.node.get_tx_infos(user_address)).data


class Relay(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'rawTransaction': fields.String(required=True),
    }

    @use_args(args)
    def post(self, args):
        try:
            transaction_id = self.trustlines.node.relay_tx(args['rawTransaction'])
        except ValueError:  # should mean error in relaying the transaction
            abort(409, 'There was an error while relaying this transaction')
        return transaction_id.hex()


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
        address = request.json['address']
        return self.trustlines.node.send_ether(address)


class Path(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'value': fields.Int(required=False, missing=1, validate=validate.Range(min=1)),
        'maxHops': fields.Int(required=False, missing=None),
        'maxFees': fields.Int(required=False, missing=None),
        'from': custom_fields.Address(required=True),
        'to': custom_fields.Address(required=True)
    }

    @use_args(args)
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)

        source = args['from']
        target = args['to']
        value = args['value']
        max_fees = args['maxFees']
        max_hops = args['maxHops']

        cost, path = self.trustlines.currency_network_graphs[network_address].find_path(
            source=source,
            target=target,
            value=value,
            max_fees=max_fees,
            max_hops=max_hops)

        if path:
            try:
                gas = self.trustlines.currency_network_proxies[network_address].estimate_gas_for_transfer(
                    source,
                    target,
                    value,
                    cost,
                    path[1:])
            except ValueError as e:  # should mean out of gas, so path was not right.
                gas = 0
                path = []
                cost = 0
        else:
            gas = 0

        return {'path': path,
                'estimatedGas': gas,
                'fees': cost}


class ReduceDebtPath(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'value': fields.Int(required=True, validate=validate.Range(min=1)),
        'maxHops': fields.Int(required=False, missing=None),
        'maxFees': fields.Int(required=False, missing=None),
        'from': custom_fields.Address(required=True),
        'to': custom_fields.Address(required=True),
        'via': custom_fields.Address(required=True)
    }

    @use_args(args)
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)

        source = args['from']
        target_reduce = args['to']
        target_increase = args['via']
        value = args['value']
        max_fees = args['maxFees']
        max_hops = args['maxHops']

        cost, path = self.trustlines.currency_network_graphs[network_address].find_path_triangulation(
            source=source,
            target_reduce=target_reduce,
            target_increase=target_increase,
            value=value,
            max_fees=max_fees,
            max_hops=max_hops)

        if path:
            try:
                gas = self.trustlines.currency_network_proxies[network_address].estimate_gas_for_transfer(
                    source,
                    source,
                    value,
                    cost,  # max_fee for smart contract
                    path[1:])  # the smart contract takes the sender of the message as source
            except ValueError as e:  # should mean out of gas, so path was not right.
                gas = 0
                path = []
                cost = 0
        else:
            gas = 0

        return {'path': path,
                'estimatedGas': gas,
                'fees': cost}


# CloseTrustline is similar to the above ReduceDebtPath, though it does not
# take `via` and `value` as parameters. Instead it tries to reduce the debt to
# zero and uses any contact to do so.


class CloseTrustline(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'maxHops': fields.Int(required=False, missing=None),
        'maxFees': fields.Int(required=False, missing=None),
        'from': custom_fields.Address(required=True),
        'to': custom_fields.Address(required=True),
    }

    @use_args(args)
    @dump_result_with_schema(CloseTrustlineResultSchema())
    def post(self, args, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        source = args['from']
        target_reduce = args['to']
        max_fees = args['maxFees']
        max_hops = args['maxHops']

        graph = self.trustlines.currency_network_graphs[network_address]
        balance = graph.get_balance(source, target_reduce)
        value = -balance

        def make_empty_payment_path():
            return PaymentPath(fee=0, path=[], value=value, estimated_gas=0)

        if balance == 0:
            return make_empty_payment_path()

        if balance > 0:
            raise RuntimeError("balance is positive. Cannot reduce debt in CloseTrustline resource.")

        payment_path = graph.find_best_path_triangulation(source,
                                                          target_reduce,
                                                          value,
                                                          max_hops=max_hops,
                                                          max_fees=max_fees)

        proxy = self.trustlines.currency_network_proxies[network_address]
        payment_path.estimated_gas = proxy.estimate_gas_for_payment_path(payment_path)

        if payment_path.estimated_gas == 0:
            return make_empty_payment_path()

        return payment_path


class GraphImage(MethodView):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        filename = tempfile.mktemp(".gif")
        self.trustlines.currency_network_graphs[network_address].draw(filename)
        return send_file(filename, mimetype='image/gif')


class GraphDump(MethodView):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        response = make_response(self.trustlines.currency_network_graphs[network_address].dump())
        cd = 'attachment; filename=networkdump.csv'
        response.headers['Content-Disposition'] = cd
        response.mimetype = 'text/csv'
        return response
