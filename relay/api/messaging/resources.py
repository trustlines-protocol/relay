import time

from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_args


class PostMessage(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    args = {
        'message': fields.String(required=True),
    }

    @use_args(args)
    def post(self, args, user_address):
        self.trustlines.messaging[user_address].publish({
            'message': args['message'],
            'timestamp': int(time.time())
        })
        return 'Ok'
