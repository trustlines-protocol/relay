import tempfile

from flask import request, send_file, make_response, abort
from flask.views import MethodView
from flask_restful import Resource
from webargs import fields, ValidationError
from webargs.flaskparser import use_args
from marshmallow import validate

from relay.utils import is_address, get_event_direction, get_event_from_to
from relay.currency_network import CurrencyNetwork


def validate_address(address):
    if not is_address(address):
        raise ValidationError('Not a valid address')


class NetworkList(Resource):

    def __init__(self, trustlines):
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

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address):
        return {
            'address': network_address,
            'name': self.trustlines.currency_network_proxies[network_address].name,
            'abbreviation': self.trustlines.currency_network_proxies[network_address].symbol,
            'decimals': self.trustlines.currency_network_proxies[network_address].decimals,
            'numUsers': len(self.trustlines.currency_network_proxies[network_address].users)
        }


class UserList(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address):
        return self.trustlines.currency_network_proxies[network_address].users


class User(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, user_address):
        return self.trustlines.currency_network_graphs[network_address].get_account_sum(user_address).as_dict()


class ContactList(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, user_address):
        return self.trustlines.currency_network_graphs[network_address].get_friends(user_address)


class TrustlineList(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, user_address):
        graph = self.trustlines.currency_network_graphs[network_address]
        friends = graph.get_friends(user_address)
        accounts = []
        for friend_address in friends:
            trustline = {}
            trustline.update({'address': friend_address})
            trustline.update(graph.get_account_sum(user_address, friend_address).as_dict())
            accounts.append(trustline)
        return accounts


class Trustline(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        graph = self.trustlines.currency_network_graphs[network_address]
        trustline = {}
        trustline.update({'address': b_address})
        trustline.update(graph.get_account_sum(a_address, b_address).as_dict())
        return trustline


class Spendable(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address):
        return self.trustlines.currency_network_proxies[network_address].spendable(a_address)


class SpendableTo(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        return self.trustlines.currency_network_proxies[network_address].spendableTo(a_address, b_address)


class UserEventsNetwork(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetwork.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, network_address, user_address):
        proxy = self.trustlines.currency_network_proxies[network_address]
        from_block = args['fromBlock']
        type = args['type']
        if type is not None:
            events = proxy.get_events(type, user_address, from_block=from_block)
        else:
            events = proxy.get_all_events(user_address, from_block=from_block)
        return sorted([{'blockNumber': event.get('blockNumber'),
                        'type': event.get('event'),
                        'transactionId': event.get('transactionHash'),
                        'networkAddress': event.get('address'),
                        'status': self.trustlines.node.get_block_status(event.get('blockNumber')),
                        'timestamp': self.trustlines.node.get_block_time(event.get('blockNumber')),
                        'amount': event.get('args').get('_value'),
                        'direction': get_event_direction(event, user_address)[0],
                        'address': get_event_direction(event, user_address)[1]} for event in events],
                      key=lambda x: x.get('blockNumber', 0))


class UserEvents(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetwork.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, user_address):
        events = []
        type = args['type']
        from_block = args['fromBlock']
        networks = self.trustlines.networks
        for network_address in networks:
            proxy = self.trustlines.currency_network_proxies[network_address]
            if type is not None:
                events = events + proxy.get_events(type, user_address, from_block=from_block)
            else:
                events = events + proxy.get_all_events(user_address, from_block=from_block)
        return sorted([{'blockNumber': event.get('blockNumber'),
                        'type': event.get('event'),
                        'transactionId': event.get('transactionHash'),
                        'networkAddress': event.get('address'),
                        'status': self.trustlines.node.get_block_status(event.get('blockNumber')),
                        'timestamp': self.trustlines.node.get_block_time(event.get('blockNumber')),
                        'direction': get_event_direction(event, user_address)[0],
                        'amount': event.get('args').get('_value'),
                        'address': get_event_direction(event, user_address)[1]} for event in events],
                      key=lambda x: x.get('blockNumber', 0))


class EventsNetwork(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    args = {
        'fromBlock': fields.Int(required=False, missing=0),
        'type': fields.Str(required=False,
                           validate=validate.OneOf(CurrencyNetwork.event_types),
                           missing=None)
    }

    @use_args(args)
    def get(self, args, network_address):
        proxy = self.trustlines.currency_network_proxies[network_address]
        from_block = args['fromBlock']
        type = args['type']
        if type is not None:
            events = proxy.get_events(type, from_block=from_block)
        else:
            events = proxy.get_all_events(from_block=from_block)
        return sorted([{'blockNumber': event.get('blockNumber'),
                        'type': event.get('event'),
                        'transactionId': event.get('transactionHash'),
                        'networkAddress': event.get('address'),
                        'status': self.trustlines.node.get_block_status(event.get('blockNumber')),
                        'timestamp': self.trustlines.node.get_block_time(event.get('blockNumber')),
                        'amount': event.get('args').get('_value'),
                        'from': get_event_from_to(event)[0],
                        'to': get_event_from_to(event)[1]} for event in events],
                      key=lambda x: x.get('blockNumber', 0))


class TransactionInfos(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, user_address):
        return self.trustlines.node.get_tx_infos(user_address)


class Relay(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def post(self):
        try:
            transaction_id = self.trustlines.node.relay_tx(request.json['rawTransaction'])
        except ValueError:  # should mean error in relaying the transaction
            abort(409, 'There was an error while relaying this transaction')

        return transaction_id

class Balance(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, user_address):
        return self.trustlines.node.balance(user_address)


class Block(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.node.blocknumber


class RequestEther(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def post(self):
        address = request.json['address']
        return self.trustlines.node.send_ether(address)


class Path(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    args = {
        'value': fields.Int(required=False, missing=1),
        'maxHops': fields.Int(required=False, missing=None),
        'maxFees': fields.Int(required=False, missing=None),
        'from': fields.Str(required=True, validate=validate_address),
        'to': fields.Str(required=True, validate=validate_address)
    }

    @use_args(args)
    def post(self, args, address):
        cost, path = self.trustlines.currency_network_graphs[address].find_path(
            source=args['from'],
            target=args['to'],
            value=args['value'],
            max_fees=args['maxFees'],
            max_hops=args['maxHops'])

        if path:
            try:
                gas = self.trustlines.currency_network_proxies[address].estimate_gas_for_transfer(
                    args['from'],
                    args['to'],
                    args['value'],
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

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, address):
        filename = tempfile.mktemp(".gif")
        self.trustlines.currency_network_graphs[address].draw(filename)
        return send_file(filename, mimetype='image/gif')


class GraphDump(MethodView):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, address):
        response = make_response(self.trustlines.currency_network_graphs[address].dump())
        cd = 'attachment; filename=networkdump.csv'
        response.headers['Content-Disposition'] = cd
        response.mimetype = 'text/csv'
        return response
