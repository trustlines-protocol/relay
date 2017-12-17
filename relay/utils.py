import web3


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


def get_event_from_to(event):
    types = {
        'Transfer': ['_from', '_to'],
        'BalanceUpdate': ['_from', '_to'],
        'CreditlineUpdateRequest': ['_creditor', '_debtor'],
        'CreditlineUpdate': ['_creditor', '_debtor'],
        'PathPrepared': ['_sender', '_receiver'],
        'ChequeCashed': ['_sender', '_receiver'],
    }
    _from = event.get('args')[types[event.get('event')][0]]
    _to = event.get('args')[types[event.get('event')][1]]
    return _from, _to


def get_event_direction(event, user_address):
    _from, _to = get_event_from_to(event)
    if _from == user_address:
        return ('sent', _to)
    else:
        return ('received', _from)


def sha3(text):
    return web3.Web3.sha3(text=text)
