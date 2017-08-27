import tempfile

from flask import request, send_file, make_response
from flask.views import MethodView
from flask_restful import Resource
from webargs import fields, ValidationError
from webargs.flaskparser import use_args

from relay.utils import is_address,  merge_two_dicts, trim_args


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

    def get(self, address):
        return {
            'address': address,
            'name': self.trustlines.currency_network_proxies[address].name,
            'abbreviation': self.trustlines.currency_network_proxies[address].symbol,
            'decimals': self.trustlines.currency_network_proxies[address].decimals,
            'numUsers': len(self.trustlines.currency_network_proxies[address].users)
        }


class UserList(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, address):
        return self.trustlines.currency_network_proxies[address].users


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
            trustline.update({'bAddress': friend_address})
            trustline.update(graph.get_account_sum(user_address, friend_address).as_dict())
            accounts.append(trustline)
        return accounts


class Trustline(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        graph = self.trustlines.currency_network_graphs[network_address]
        return graph.get_account_sum(a_address, b_address).as_dict()


class Spendable(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address):
        return {
            'totalSpendable': self.trustlines.currency_network_proxies[network_address].spendable(a_address)
        }


class SpendableTo(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address):
        return {
            'spendable': self.trustlines.currency_network_proxies[network_address].spendableTo(a_address, b_address)
        }


class Event(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, user_address):
        proxy = self.trustlines.currency_network_proxies[network_address]
        fromBlock = int(request.args.get('fromBlock', 0))
        if request.args.get('type') is not None:
            events = proxy.get_event(request.args.get('type'), user_address, fromBlock)
        else:
            events = proxy.get_all_events(user_address, fromBlock)
        return sorted([
            merge_two_dicts(
                trim_args(event.get('args')),
                {
                    'blockNumber': event.get('blockNumber'),
                    'event': event.get('event'),
                    'transactionHash': event.get('transactionHash'),
                    'status': 'pending' if event.get('blockNumber') is None else 'confirmed'
                }
            ) for event in events], key=lambda x: x.get('blockNumber', 0))


class EventList(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, user_address):
        events = []
        type = request.args.get('type', None)
        fromBlock = int(request.args.get('fromBlock', 0))
        networks = self.trustlines.get_networks_of_user(user_address)
        for network_address in networks:
            proxy = self.trustlines.currency_network_proxies[network_address]
            if type is not None:
                events = events + proxy.get_event(type, user_address, fromBlock)
            else:
                events = events + proxy.get_all_events(user_address, fromBlock)
        return sorted([
            merge_two_dicts(
                trim_args(event.get('args')),
                {
                    'blockNumber': event.get('blockNumber'),
                    'event': event.get('event'),
                    'transactionHash': event.get('transactionHash'),
                    'networkAddress': event.get('address'),
                    'status': 'pending' if event.get('blockNumber') is None else 'confirmed'
                }
            ) for event in events], key=lambda x: x.get('blockNumber', 0))


class TransactionInfos(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, user_address):
        return self.trustlines.node.get_tx_infos(user_address)


class Relay(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def post(self):
        return self.trustlines.node.relay_tx(request.json['rawTransaction'])


class Balance(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, user_address):
        return {
            'balance': self.trustlines.node.balance(user_address)
        }


class Block(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return {
            'blocknumber': self.trustlines.node.blocknumber
        }


class RequestEther(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def post(self):
        address = request.json['address']
        return {
            'txhash': self.trustlines.node.send_ether(address)
        }


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

        #gas = self.trustlines.currency_network_proxies[address].estimate_gas_for_transfer(
        #    args['from'],
        #    args['to'],
        #    args['value'],
        #    cost*2,
        #    path)
        return {'path': path,
                'estimatedGas': 0,
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


