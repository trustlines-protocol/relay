import time

from flask_restful import Resource
from webargs import fields
from webargs.flaskparser import use_args

from relay.events import MessageEvent
from relay.relay import TrustlinesRelay


class PostMessage(Resource):
    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    args = {
        "message": fields.String(required=True),
        "type": fields.String(missing=None),
    }

    @use_args(args)
    def post(self, args, user_address: str):
        self.trustlines.messaging[user_address].publish(
            MessageEvent(args["message"], type=args["type"], timestamp=int(time.time()))
        )
        return "Ok"
