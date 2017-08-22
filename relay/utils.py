import re


def add_0x_prefix(value):
    if value[0:2] == '0x':
        return value
    return '0x' + value


def is_address(address):
    return re.match(r"^(0x)?[0-9a-f]{40}", str(address)) is not None

def merge_two_dicts(x, y):
    """Given two dicts, merge them into a new dict as a shallow copy."""
    z = x.copy()
    z.update(y)
    return z
