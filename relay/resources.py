from flask import request
from flask_restful import  Resource
from utils import merge_two_dicts


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

class Path(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, network_address, a_address, b_address, value):
        graph = self.trustlines.currency_network_graphs[network_address]
        return {
            'path': graph.find_path(a_address, b_address, value),
            'maxFee': value * 0.01 # TODO calculate in graph
        }

class Event(Resource):

    def __init__(self, trustlines):
	self.trustlines = trustlines

    def get(self, network_address, user_address):
    	types = {
    	    'Transfer': ['_from', '_to'],
            'BalanceUpdate': ['_from', '_to'],
    	    'CreditlineUpdateRequest': ['_creditor', '_debtor'],
    	    'CreditlineUpdate': ['_creditor', '_debtor'],
    	    'PathPrepared': ['_sender', '_receiver'],
    	    'ChequeCashed': ['_sender', '_receiver'],
    	}
    	params_1 = {
            'filter': { types[request.args.get('type')][0]: user_address },
            'fromBlock': int(request.args.get('fromBlock'))
        }
    	params_2 = {
            'filter': { types[request.args.get('type')][1]: user_address },
            'fromBlock': int(request.args.get('fromBlock'))
        }
        proxy = self.trustlines.currency_network_proxies[network_address]
        list_1 = proxy.get_filter(request.args.get('type'), params_1)
        list_2 = proxy.get_filter(request.args.get('type'), params_2)
    	return sorted([merge_two_dicts(event.get('args'), {'blockNumber': event.get('blockNumber'), 'event': event.get('event'), 'transactionHash': event.get('transactionHash')})
            for event in list_1 + list_2], key=lambda x: x.get('blockNumber', 0))


class TransactionInfos(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, address):
        return self.trustlines.node.get_tx_infos(address)


class Relay(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def post(self):
        return self.trustlines.node.relay_tx(request.json['rawTransaction'])


class Balance(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, address):
        return {
            'balance': self.trustlines.node.balance(address)
        }


class Block(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return {
            'blocknumber': self.trustlines.node.blocknumber
        }
