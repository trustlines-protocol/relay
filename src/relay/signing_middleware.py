"""Provide a signing middleware that automatically signs transactions

We save us from keeping track of nonces by asking parity for the next
nonce and serializing 'eth_sendTransaction' requests. The actual
signing is done by the web3 signing middleware.

This module kinds of replaces running parity with an unlocked account
"""

import copy
import logging

import eth_utils
from web3.middleware import construct_sign_and_send_raw_middleware

from relay.concurrency_utils import synchronized

logger = logging.getLogger(__name__)


@synchronized
def _eth_send_transaction(make_request, w3, method, params):
    """Run a eth_sendTransaction request

determines next nonce to be used for the eth_sendTransaction
request, sets that nonce and executes the request. The @synchronized
decorator will make sure only one _eth_send_transaction runs at the same time.

This uses the parity_nextNonce function, hence it only works with
parity.
"""
    assert method == "eth_sendTransaction"
    if "nonce" not in params[0]:
        params[0]["nonce"] = int(
            w3.manager.request_blocking("parity_nextNonce", [params[0]["from"]]), 16
        )
    nonce = params[0]["nonce"]
    logger.debug("_eth_send_transaction start: nonce=%s %s", nonce, params)

    res = make_request(method, params)
    logger.debug("_eth_send_transaction return: nonce=%s %s", nonce, res)
    return res


def make_prepare_signing_middleware(default_from_address):
    """
    The web3.middleware.signing middleware needs the from field to be set, which we do here.
    """

    def prepare_signing_middleware(make_request, w3):
        def middleware(method, params):
            if method != "eth_sendTransaction":
                return make_request(method, params)
            from_address = params[0].get("from")
            if from_address is not None and not eth_utils.is_same_address(
                from_address, default_from_address
            ):
                return make_request(method, params)
            params = copy.deepcopy(params)
            params[0]["from"] = default_from_address
            return _eth_send_transaction(make_request, w3, method, params)

        return middleware

    return prepare_signing_middleware


def install_signing_middleware(w3, account):
    if w3.eth.defaultAccount:
        raise RuntimeError("default account already set")
    w3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))
    w3.eth.defaultAccount = account.address
    w3.middleware_onion.add(make_prepare_signing_middleware(account.address))
