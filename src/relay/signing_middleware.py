"""Provide a signing middleware that automatically signs transactions


"""
import copy

from web3.middleware import construct_sign_and_send_raw_middleware


def make_set_from_address_middleware(default_from_address):
    """
    The web3.middleware.signing middleware needs the from field to be set, which we do here.
    """

    def set_from_middleware(make_request, w3):
        def middleware(method, params):
            if method != "eth_sendTransaction":
                return make_request(method, params)
            if "from" in params[0]:
                return make_request(method, params)

            params = copy.deepcopy(params)
            params["from"] = default_from_address
            return make_request(method, params)

        return middleware

    return set_from_middleware


def install_signing_middleware(w3, account):
    w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    w3.eth.defaultAccount = account.address
    w3.middleware_onion.add(make_set_from_address_middleware(account.address))
