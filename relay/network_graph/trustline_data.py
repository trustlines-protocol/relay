""" Accessor methods for trustline data
    The data of a trustline is stored in a data object on an edge of u and v
    Because the data is only stored once but has a different meaning for u and v, this
    accessors help to get the values from the correct point of view.
"""
from relay.network_graph.graph_constants import (balance_ab,
                                                 creditline_ab,
                                                 creditline_ba,
                                                 interest_ab,
                                                 interest_ba,
                                                 fees_outstanding_a,
                                                 fees_outstanding_b, m_time)


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
    return get(user, counter_party, data[balance_ab], -data[balance_ab])


def set_balance(data, user, counter_party, balance):
    set(data,
        user,
        counter_party,
        {balance_ab: balance},
        {balance_ab: -balance})


def get_creditline(data, user, counter_party):
    return get(user, counter_party, data[creditline_ab], data[creditline_ba])


def set_creditline(data, user, counter_party, creditline):
    set(data, user, counter_party, {creditline_ab: creditline}, {creditline_ba: creditline})


def get_interest_rate(data, user, counter_party):
    return get(user, counter_party, data[interest_ab], data[interest_ba])


def set_interest_rate(data, user, counter_party, interest_rate):
    set(data, user, counter_party, {interest_ab: interest_rate}, {interest_ba: interest_rate})


def get_fees_outstanding(data, user, counter_party):
    return get(user, counter_party, data[fees_outstanding_a], data[fees_outstanding_b])


def set_fees_outstanding(data, user, counter_party, fees_outstanding):
    set(data, user, counter_party, {fees_outstanding_a: fees_outstanding}, {fees_outstanding_b: fees_outstanding})


def get_mtime(data):
    return data[m_time]


def set_mtime(data, timestamp):
    data[m_time] = timestamp
