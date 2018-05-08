import web3  # type: ignore
import re


def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z


def trim_args(args):
    trimmed_args = {}
    for key in args:
        trimmed_args[key[1:len(key)]] = args[key]
    return trimmed_args


def sha3(text: str) -> str:
    return web3.Web3.sha3(text=text)


def to_snake_case(camel_str: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
