import pkg_resources
import web3


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


def trim_args(args):
    trimmed_args = {}
    for key in args:
        trimmed_args[key[1 : len(key)]] = args[key]
    return trimmed_args


def sha3(text: str) -> str:
    return web3.Web3.keccak(text=text).hex()


def get_version():
    try:
        return pkg_resources.get_distribution("trustlines-relay").version
    except pkg_resources.DistributionNotFound:
        return "<UNKNOWN>"
