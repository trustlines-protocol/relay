def calculate_fees(imbalance_generated, capacity_imbalance_fee_divisor):
    if capacity_imbalance_fee_divisor == 0 or imbalance_generated == 0:
        return 0
    return (imbalance_generated - 1) // capacity_imbalance_fee_divisor + 1


def calculate_fees_reverse(imbalance_generated, capacity_imbalance_fee_divisor):
    if capacity_imbalance_fee_divisor == 0 or imbalance_generated == 0:
        return 0
    return (imbalance_generated - 1) // (capacity_imbalance_fee_divisor - 1) + 1


def imbalance_generated(*, value, balance):
    assert value >= 0

    if balance <= 0:
        return value

    return max(value - balance, 0)


def estimate_fee_from_imbalance(divisor, imbalance):

    if (imbalance <= 0):
        fee_estimation = 0
    else:
        fee_estimation = (imbalance // divisor) + 1

    fee_estimation -= fee_estimation // divisor

    return fee_estimation


def estimate_sendable_from_one_limiting_capacity(divisor, capacity, balance, number_of_hops_to_destination):
    """Estimates the max sendable amount in a path where the limiting capacity is assumed to be in a single trustline
    with given capacity, balance, and that is number_of_hops_to_destination from the destination"""

    if divisor == 0:
        return capacity

    if number_of_hops_to_destination == 0:
        return capacity

    imbalance = capacity

    if balance > 0:
        imbalance -= balance

    fee_estimation = estimate_fee_from_imbalance(divisor, imbalance)

    max_sendable = capacity - fee_estimation

    #fee_estimation = int((1+capacity/divisor)/(1+1/divisor))
    #max_sendable = capacity - fee_estimation
    return estimate_sendable_from_one_limiting_capacity(divisor, max_sendable, balance, number_of_hops_to_destination - 1)


def estimate_sendable(divisor, path_capacities, path_balances):
    """Estimates the max sendable amount in a path with given capacities and balances"""
    for i in range(len(path_capacities)-1):

        current_sendable = estimate_sendable_from_one_limiting_capacity(divisor, path_capacities[i], path_balances[i], i+1)
        next_capacity = path_capacities[i+1]

        if current_sendable < next_capacity:
            path_capacities[i+1] = current_sendable

    return estimate_sendable_from_one_limiting_capacity(divisor, path_capacities[len(path_capacities)-1], path_balances[len(path_capacities)-1], 1)
