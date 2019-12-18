""" Accessor methods for trustline data
    The data of a trustline is stored in a data object on an edge of u and v
    Because the data is only stored once but has a different meaning for u and v, this
    accessors help to get the values from the correct point of view.
"""
from relay.network_graph.graph_constants import (
    balance_ab,
    creditline_ab,
    creditline_ba,
    interest_ab,
    interest_ba,
    is_frozen,
    m_time,
)


def get(user, counter_party, value, reverse_value):
    if user < counter_party:
        return value
    else:
        return reverse_value


def set(data, user, counter_party, setter_dict, reverse_setter_dict):
    if user < counter_party:
        for key, value in setter_dict.items():
            data[key] = value
    else:
        for key, value in reverse_setter_dict.items():
            data[key] = value


def get_balance(data, user, counter_party):
    """Returns the balance between user and counter_party from the view of user
    A positive balance means that counter_party ows user, or in other words, that
    user has a claim against counter_party over this amount
    """
    return get(user, counter_party, data[balance_ab], -data[balance_ab])


def set_balance(data, user, counter_party, balance):
    """Sets the balance between user and counter_party from the view of user"""
    set(data, user, counter_party, {balance_ab: balance}, {balance_ab: -balance})


def get_creditline(data, user, counter_party):
    """Returns the creditline given by user to counter_party
    This is the maximum amount that counter_party is allowed to owe to user

    To get the creditline given by counter_party to user, you can use `get_creditline(data, counter_party, user)`
    """
    return get(user, counter_party, data[creditline_ab], data[creditline_ba])


def set_creditline(data, user, counter_party, creditline):
    """Sets the creditline given by user to counter_party
    This sets the maximum amount that counter_party can owe to user

    To set the creditline given by counter_party to user,
    you can use `set_creditline(data, counter_party, user, creditline)`
    """
    set(
        data,
        user,
        counter_party,
        {creditline_ab: creditline},
        {creditline_ba: creditline},
    )


def get_interest_rate(data, user, counter_party):
    """Returns the interest rate of the credit given from user to counter_party"""
    return get(user, counter_party, data[interest_ab], data[interest_ba])


def set_interest_rate(data, user, counter_party, interest_rate):
    """Sets the interest rate of the credit given from user to counter_party"""
    set(
        data,
        user,
        counter_party,
        {interest_ab: interest_rate},
        {interest_ba: interest_rate},
    )


def get_is_frozen(data):
    return data[is_frozen]


def set_is_frozen(data, _is_frozen):
    data[is_frozen] = _is_frozen


def get_mtime(data):
    """Returns the unix timestamp of the last modification time of this trustline"""
    return data[m_time]


def set_mtime(data, timestamp):
    """Sets the unix timestamp of the last modification time of this trustline"""
    data[m_time] = timestamp
