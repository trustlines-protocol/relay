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


def estimate_sendable_from_one_limiting_capacity(divisor, capacity, balance, number_of_hops_to_target):
    """Estimates the max sendable amount in a path where the limiting capacity is assumed to be in a single trustline
    with given capacity, balance, and that is number_of_hops_to_target away from the target"""

    if divisor == 0:
        return capacity

    if number_of_hops_to_target == 0:
        return capacity

    imbalance = imbalance_generated(value=capacity, balance=balance)
    fee_estimation = calculate_fees(imbalance, divisor)

    max_sendable = capacity - fee_estimation

    return estimate_sendable_from_one_limiting_capacity(divisor,
                                                        max_sendable,
                                                        balance,
                                                        number_of_hops_to_target - 1)


def estimate_sendable(divisor, path_capacities, path_balances):
    """Estimates the max sendable amount in a path with given capacities and balances"""

    number_of_hops_to_target = len(path_capacities) - 1
    min_sendable = float('inf')

    for i in range(len(path_capacities)):

        current_sendable = estimate_sendable_from_one_limiting_capacity(divisor,
                                                                        path_capacities[i],
                                                                        path_balances[i],
                                                                        number_of_hops_to_target)

        if current_sendable < min_sendable:
            min_sendable = current_sendable

        number_of_hops_to_target -= 1

    return min_sendable
