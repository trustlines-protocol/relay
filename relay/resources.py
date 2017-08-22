from flask import request
from flask_restful import  Resource


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

    	def _from_to():
    	    return {'_from': [user_address], '_to': [user_address]}

    	def _creditor_debtor():
    	    return {'_creditor': [user_address], '_debtor': [user_address]}

    	def _sender_receiver():
    	    return {'_sender': [user_address], '_receiver': [user_address]}

    	types = {
    	    'Transfer': _from_to,
        	'BalanceUpdate': _from_to,
    	    'CreditlineUpdateRequest': _creditor_debtor,
    	    'CreditlineUpdate': _creditor_debtor,
    	    'PathPrepared': _sender_receiver,
    	    'ChequeCashed': _sender_receiver,
    	}

    	proxy = self.trustlines.currency_network_proxies[network_address]
    	params = {'filter': types[request.args.get('type')](), 'fromBlock': request.args.get('fromBlock')}
    	return proxy.get_filter(request.args.get('type'), params)


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
