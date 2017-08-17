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

    def get(self, todo_id):
        pass


class TrustlineList(Resource):

    def get(self, todo_id):
        pass


class Trustline(Resource):

    def get(self, todo_id):
        pass


class TransactionInfos(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self, address):
        return self.trustlines.node.get_tx_infos(address)


class Relay(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def post(self):
        return self.trustlines.node.relay_tx(request.form['rawTransaction'])


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
