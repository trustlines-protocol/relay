from flask_restful import Resource

from relay.relay import TrustlinesRelay


class TokenAddresses(Resource):

    def __init__(self, trustlines):
        self.trustlines = trustlines

    def get(self):
        return self.trustlines.unw_eth + self.trustlines.tokens


class TokenBalance(Resource):

    def __init__(self, trustlines: TrustlinesRelay) -> None:
        self.trustlines = trustlines

    def get(self, token_address: str, user_address: str):
        if (token_address in self.trustlines.unw_eth):
            return self.trustlines.unw_eth_proxies[token_address].balance_of(user_address)
        if (token_address in self.trustlines.tokens):
            return self.trustlines.token_proxies[token_address].balance_of(user_address)
