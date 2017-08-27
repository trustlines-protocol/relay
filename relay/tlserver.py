#!/usr/bin/env python
from __future__ import print_function
import tempfile
import logging
import json
import traceback

from flask import Flask, jsonify, request, send_file, make_response
from flask_sockets import Sockets
from flask_cors import CORS
from gevent.wsgi import WSGIServer
from gevent.event import Event
from geventwebsocket.handler import WebSocketHandler
from geventwebsocket import WebSocketError
from werkzeug.routing import BaseConverter, ValidationError

from tlhelper import Trustline
from tlgraph import Community
from utils import is_address, add_0x_prefix
from logger import getLogger


logger = getLogger('tlserver', logging.DEBUG)


app = Flask(__name__)
sockets = Sockets(app)
CORS(app)  # to allow CROSS ORIGIN
trustline = Trustline()
trustline.initialise_app()
communities = {}
wsevents = {}


class AddressConverter(BaseConverter):

    def to_python(self, value):
        if not is_address(value):
            value = trustline.get_address(value)
            if not is_address(value):
                raise ValidationError()
            return value
        value = add_0x_prefix(value)
        return value

    def to_url(self, value):
        if not is_address(value):
            raise ValueError("Not a valid address")
        return add_0x_prefix(value)
app.url_map.converters['address'] = AddressConverter
sockets.url_map.converters['address'] = AddressConverter


class TokenAddressConverter(AddressConverter):

    def to_python(self, value):
        value = super(TokenAddressConverter, self).to_python(value)
        if value not in trustline.get_token_list():
            raise ValidationError()
        return value
app.url_map.converters['token_address'] = TokenAddressConverter
sockets.url_map.converters['token_address'] = TokenAddressConverter

def ws_loop(ws, notifier_address, function):
    wsevents.setdefault(notifier_address, Event())
    while True:
        try:
            json_obj = json.dumps(function())
        except Exception as err:
            json_obj = json.dumps(
                make_error_obj('500',
                               'The server encountered an internal error and was unable to complete your request'
                               ))
            traceback.print_exc()
        try:
            ws.send(json_obj)
        except WebSocketError:
            break
        wsevents[notifier_address].wait()


@app.route('/api/tokens/', methods=['POST'])
def create_token():
    if not request.json or 'name' not in request.json\
            or 'symbol' not in request.json:
        return make_error(400, 'Request Parameters not present')
    name = request.json.get('name')
    symbol = request.json.get('symbol')
    try:
        decimal = int(request.json.get('decimal'))
    except Exception:
        return make_error(400, 'Invalid decimal, ')
    address = str(trustline.create_token(name, symbol, decimal))
    communities[address] = Community()
    return jsonify({'address': address})


@app.route('/api/tokens/', methods=['GET'])
def get_token_list():
    return jsonify({'tokens': [{'address' : address,
                                'name' : trustline.get_name(address)} for address in trustline.get_token_list()]})


@app.route('/api/tokens/<token_address:token_address>/users/<address:user_address>/friends', methods=['GET'])
def get_friends(token_address, user_address):
    return jsonify({'friends': communities[token_address].get_friends(user_address)})


def get_accounts(token_address, user_address):
    friends = communities[token_address].get_friends(user_address)
    accounts = {}
    for friend_address in friends:
        accounts[friend_address] = communities[token_address].get_account_sum(user_address, friend_address).as_dict()
    return {'accounts': accounts}


@app.route('/api/tokens/<token_address:token_address>/users/<address:user_address>/accounts/', methods=['GET'])
def get_accounts_rest(token_address, user_address):
    return jsonify(get_accounts(token_address, user_address))


@sockets.route('/api/tokens/<token_address:token_address>/users/<address:user_address>/accounts/')
def get_accounts_ws(ws, token_address, user_address):
    ws_loop(ws, user_address, lambda: get_accounts(token_address, user_address))


def get_account(token_address, a_address, b_address):
    account = communities[token_address].get_account_sum(a_address, b_address).as_dict()
    return {'account': account}


@app.route('/api/tokens/<token_address:token_address>/users/<address:a_address>/accounts/<address:b_address>', methods=['GET'])
def get_account_rest(token_address, a_address, b_address):
    return jsonify(get_account(token_address, a_address, b_address))


@sockets.route('/api/tokens/<token_address:token_address>/users/<address:a_address>/accounts/<address:b_address>')
def get_account_ws(ws, token_address, a_address, b_address):
    ws_loop(ws, a_address, lambda: get_account(token_address, a_address, b_address))


def get_user_info(token_address, a_address):
    account = communities[token_address].get_account_sum(a_address).as_dict()
    return {'account': account}


@app.route('/api/tokens/<token_address:token_address>/users/<address:a_address>')
def get_user_info_rest(token_address, a_address):
    return jsonify(get_user_info(token_address, a_address))


@sockets.route('/api/tokens/<token_address:token_address>/users/<address:a_address>')
def get_user_info_ws(ws, token_address, a_address):
    ws_loop(ws, a_address, lambda: get_user_info(token_address, a_address))


@app.route('/api/tokens/<token_address:token_address>', methods=['GET'])
def get_token_info(token_address):
    token_info = trustline.get_token_info(token_address)
    token_info['created'] = communities[token_address].money_created
    token_info['creditlines'] = communities[token_address].total_creditlines
    return jsonify({'tokenInfo': token_info})


@app.route('/api/tokens/<token_address:token_address>/users/', methods=['GET'])
def get_users(token_address):
    return jsonify({'users': communities[token_address].users})


@app.route('/api/newuser/<address:user_address>', methods=['PUT'])
def new_user(user_address):
    return jsonify({'transfer': trustline.new_user(user_address)})


# @app.route('/api/name/<address:token_name>', methods=['GET'])
def get_token_address(token_name):
    return jsonify({'token_address': trustline.get_token_address(token_name)})


@app.route('/api/tokenabi', methods=['GET'])
def get_token_abi():
    return jsonify({'abi': trustline.get_token_abi()})


@app.route('/api/txinfos/<address:user_address>', methods=['GET'])
def get_tx_infos(user_address):
    return jsonify({'txinfos': trustline.get_tx_infos(user_address)})


@app.route('/api/relay', methods=['POST'])
def relay_tx():
    if not request.json or 'data' not in request.json:
        return make_error(400, 'Request Parameters not present')
    rawtxn = request.json.get('data')
    try:
        result = trustline.relay_tx(rawtxn)
    except ValueError as err:
        logger.warning('Invalid transaction: ' + str(err))
        return make_error(400, 'Invalid transaction')
    return jsonify({'tx': str(result)})


@app.route('/api/tokens/<token_address:token_address>/users/<address:a_address>/path/<address:b_address>/value/<int:value>', methods=['GET'])
def find_path(token_address, a_address, b_address, value):
    return jsonify({'path': communities[token_address].find_path(a_address, b_address, value)})


#  for testing
# @app.route('/api/test/tokens/<address:token_address>/users/<address:a_address>/accounts/<address:b_address>', methods=['PUT'])
def update_trustline(token_address, a_address, b_address):
    if not request.json or 'value' not in request.json:
        return make_error(400, 'Request Parameters not present')
    value = int(request.json.get('value'))
    trustline.update_trustline(token_address, a_address,b_address, value)
    return jsonify({'trustline': value})


@app.route('/api/tokens/<token_address:token_address>/users/<address:user_address>/block/<string:from_block>/transfers', methods=['GET'])
def list_transfers(token_address, user_address, from_block):
    try:
        from_block = long(from_block)
    except Exception as err:
        return make_error(400, 'Error in getting transfers for the user' + str(err))
    return jsonify({'transfers': trustline.list_transfers(token_address, user_address, from_block)})


def poll_events(token_address, user_address, from_block):
    return {'events': trustline.poll_events(token_address, user_address, from_block), 'block': trustline.get_block()}


@app.route('/api/tokens/<token_address:token_address>/users/<address:user_address>/block/<int:from_block>/events', methods=['GET'])
def poll_events_rest(token_address, user_address, from_block):
    try:
        from_block = long(from_block)
    except Exception as err:
        return make_error(400, 'Error in getting the events for the user' + str(err))
    return jsonify(poll_events(token_address, user_address, from_block))


@sockets.route('/api/tokens/<token_address:token_address>/users/<address:user_address>/block/<int:from_block>/events')
def poll_events_ws(ws, token_address, user_address, from_block):
    from_block_dict = {'fb': long(from_block)}  # scoping hack

    def f():
        result = poll_events(token_address, user_address, from_block_dict['fb'])
        from_block_dict['fb'] = result['block']
        return result

    ws_loop(ws, user_address, f)


@app.route('/api/block/', methods=['GET'])
def get_block():
    return jsonify({'block': trustline.get_block()})


@app.route('/api/tokens/<token_address:token_address>/image')
def get_image(token_address):
    filename = tempfile.mktemp(".gif")
    communities[token_address].draw(filename)
    return send_file(filename, mimetype='image/gif')


@app.route('/api/tokens/<token_address:token_address>/csv')
def get_dump(token_address):
    response = make_response(communities[token_address].dump())
    cd = 'attachment; filename=networkdump.csv'
    response.headers['Content-Disposition'] = cd
    response.mimetype = 'text/csv'
    return response



@app.errorhandler(404)
def not_found(error):
    return make_error(404, 'The resource was not found on the server')


@app.errorhandler(500)
def internal_error(error):
    return make_error(500, 'The server encountered an internal error and was unable to complete your request')


def make_error_obj(status_code, message):
    return {
        'status': status_code,
        'message': message,
    }


def make_error(status_code, message):
    response = jsonify(make_error_obj(status_code, message))
    response.status_code = status_code
    return response


def load_communities():
    for address in trustline.get_token_list():
        communities[address] = Community()


def notify(address):
    if address in wsevents:
        wsevents[address].set()
        wsevents[address].clear()


def create_on_balance(community):
    def update_balance(a, b, balance):
        notify(a)
        notify(b)
        community.update_balance(a, b, balance)
    return update_balance


def create_on_trustline(community):
    def update_balance(a, b, balance):
        notify(a)
        notify(b)
        community.update_trustline(a, b, balance)
    return update_balance


def create_on_full_sync(community):
    def update_community(graph):
        logger.info('Syncing whole graph.. ')
        community.gen_network(graph)
        logger.info('Syncing whole graph done!')
    return update_community


def start_listen():
    for address, community in communities.iteritems():
        trustline.start_listen_on_full_sync(address, create_on_full_sync(community))
        trustline.start_listen_on_balance(address, create_on_balance(community))
        trustline.start_listen_on_trustline(address, create_on_trustline(community))
        trustline.start_listen_on_transfer(address)


if __name__ == '__main__':
    ipport = ('', 5000)
    logger.info('Starting server')
    load_communities()
    start_listen()
    http_server = WSGIServer(ipport, app, handler_class=WebSocketHandler, log=None)
    logger.info('Server is running on {}'.format(ipport))
    http_server.serve_forever()
