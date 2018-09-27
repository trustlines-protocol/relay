import time

from .graph_constants import *


def calculate_interests(balance, rate, old_time, new_time):
    return balance * (new_time - old_time) / (60 * 60 * 24 * 365) * rate / 100000


def balance_with_interest_estimation(data):
    """Returns an updated balance that take into account interest
    a and b play symmetrical roles"""
    new_time = time.time()

    if data[balance_ab] > 0:  # b owes a
        interest = calculate_interests(data[balance_ab], data[interest_ab], data[m_time], new_time)
    else:  # a owes b
        interest = calculate_interests(data[balance_ab], data[interest_ba], data[m_time], new_time)

    return data[balance_ab] + interest
