from flask_restful import Resource
from webargs.flaskparser import use_args
from webargs import fields

from relay.relay import TrustlinesRelay


class AddClientToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        'clientToken': fields.String(required=True),
    }

    @use_args(args)
    def post(self, args, user_address: str):
        self.trustlines.add_push_client_token(user_address, args['clientToken'])
        return 'Ok'


class DeleteClientToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def delete(self, user_address: str, client_token: str):
        self.trustlines.delete_push_client_token(user_address, client_token)
        return 'Ok'
