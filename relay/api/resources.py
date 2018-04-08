import tempfile
from typing import List  # noqa: F401

from flask import request, send_file, make_response, abort
from flask.views import MethodView
from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_args
from marshmallow import validate

from relay.utils import sha3
from relay.blockchain.currency_network_proxy import CurrencyNetworkProxy
from relay.blockchain.events import BlockchainEvent  # noqa: F401
from relay.api import fields as custom_fields
from .schemas import CurrencyNetworkEventSchema, UserCurrencyNetworkEventSchema
from relay.relay import TrustlinesRelay


def abort_if_unknown_network(trustlines, network_address):
    if network_address not in trustlines.networks:
        abort(404, 'Unkown network: {}'.format(network_address))


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
        return self.trustlines.currency_network_graphs[network_address].get_account_sum(user_address).as_dict()


class ContactList(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.currency_network_graphs[network_address].get_friends(user_address)


class TrustlineDao(object):
    def __init__(self, network_address: str, a_address: str, b_address: str, account_sum: str) -> None:
        self.network_address = network_address
        self.a_address = a_address
        self.b_address = b_address
        self.account_sum = account_sum

    @property
    def id(self):
        if self.a_address < self.b_address:
            return sha3(self.network_address + self.a_address + self.b_address)
        else:
            return sha3(self.network_address + self.b_address + self.a_address)

    def as_dict(self):
        trustline = {
            'address': self.b_address,
            'id': self.id
        }
        trustline.update(self.account_sum.as_dict())
        return trustline


class Trustline(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        abort_if_unknown_network(self.trustlines, network_address)
        graph = self.trustlines.currency_network_graphs[network_address]
        trustline = TrustlineDao(network_address, a_address, b_address, graph.get_account_sum(a_address, b_address))
        return trustline.as_dict()


class TrustlineList(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, user_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        graph = self.trustlines.currency_network_graphs[network_address]
        friends = graph.get_friends(user_address)
        accounts = []
        for friend_address in friends:
            trustline = TrustlineDao(network_address,
                                     user_address,
                                     friend_address,
                                     graph.get_account_sum(user_address, friend_address))
            accounts.append(trustline.as_dict())
        return accounts


class Spendable(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address: str, a_address: str):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.currency_network_proxies[network_address].spendable(a_address)


class SpendableTo(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        abort_if_unknown_network(self.trustlines, network_address)
        return self.trustlines.currency_network_proxies[network_address].spendableTo(a_address, b_address)


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
        proxy = self.trustlines.currency_network_proxies[network_address]
        from_block = args['fromBlock']
        type = args['type']
        if type is not None:
            events = proxy.get_network_events(type, user_address, from_block=from_block)
        else:
            events = proxy.get_all_network_events(user_address, from_block=from_block)
        return UserCurrencyNetworkEventSchema().dump(events, many=True).data


class UserEvents(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetworkProxy.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, user_address: str):
        events = []  # type: List[BlockchainEvent]
        type = args['type']
        from_block = args['fromBlock']
        networks = self.trustlines.networks
        for network_address in networks:
            proxy = self.trustlines.currency_network_proxies[network_address]
            if type is not None:
                events = events + proxy.get_network_events(type, user_address, from_block=from_block)
            else:
                events = events + proxy.get_all_network_events(user_address, from_block=from_block)
        return UserCurrencyNetworkEventSchema().dump(events, many=True).data


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
        proxy = self.trustlines.currency_network_proxies[network_address]
        from_block = args['fromBlock']
        type = args['type']
        if type is not None:
            events = proxy.get_events(type, from_block=from_block)
        else:
            events = proxy.get_all_events(from_block=from_block)
        return CurrencyNetworkEventSchema().dump(events, many=True).data


class TransactionInfos(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, user_address: str):
        return self.trustlines.node.get_tx_infos(user_address)


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

        return transaction_id


class Balance(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, user_address: str):
        return self.trustlines.node.balance(user_address)


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
        'value': fields.Int(required=False, missing=1),
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
                    cost*2,
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
