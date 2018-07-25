from flask import abort
from flask_restful import Resource

from relay.relay import TrustlinesRelay, TokenNotFoundException, InvalidClientTokenException


class AddClientToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def put(self, user_address: str, client_token: str):
        try:
            self.trustlines.add_push_client_token(user_address, client_token)
        except InvalidClientTokenException:
            abort(422, 'Invalid Token')
        return 'Ok'


class DeleteClientToken(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def delete(self, user_address: str, client_token: str):
        try:
            self.trustlines.delete_push_client_token(user_address, client_token)
        except TokenNotFoundException:
            abort(404, 'Token not found')
        return 'Ok'
