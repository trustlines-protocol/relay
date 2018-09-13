import time

def calculate_interests(balance, rate, old_time, new_time):
    return balance * (new_time - old_time) / (60 * 60 * 24 * 365) * rate / 100000

def apply_interests(a, b, data):
    """Applies the interest to the balance in data. The interpretation of data depends on whether a < b.
    a and b play symmetrical roles"""
    # apparently not, need to refactor
    new_time = time.time()

    # I assume interest_ba is the interest given by b to a. This might be wrong.
    if a < b:
        if data['balance_ab'] > 0:  # b owes a
            interest = calculate_interests(data['balance_ab'], data['interest_ab'], data['m_time'], new_time)
        else:  # a owes b
            interest = calculate_interests(data['balance_ab'], data['interest_ba'], data['m_time'], new_time)
    else:
        if data['balance_ab'] > 0:  # a owes b
            interest = calculate_interests(data['balance_ab'], data['interest_ab'], data['m_time'], new_time)
        else:  # b owes a
            interest = calculate_interests(data['balance_ab'], data['interest_ba'], data['m_time'], new_time)

    data['balance_ab'] = data['balance_ab'] + interest
    data['m_time'] = new_time
