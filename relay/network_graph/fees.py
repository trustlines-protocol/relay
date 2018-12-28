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


def estimate_max_fee_from_max_imbalance(divisor, imbalance):
    """Gives a higher limit on the possible fee on a transfer bringing imbalance so that
    fee_actual(imbalance - fee_estimation) <= fee_estimation
    this function should estimate what needs to be substracted to imbalance to make it sendable"""

    # TODO: either improve this function or remove it and use calculate_fees_reverse

    if (imbalance <= 0):
        fee_estimation = 0
    else:
        # fee_estimation = (imbalance - 1) // (divisor - 1) + 1  # fees you would pay if you sent imbalance
        fee_estimation = (imbalance - 1) // divisor + 1
        # the error is that you should not pay fees on transferring the fees.

    # fee_estimation -= fee_estimation // divisor  # this is wrong
    # what needs to be removed is not the fee on fee_estimation but the fees on fee_actual

    # fee_estimation = int((1+capacity/divisor)/(1+1/divisor))
    # max_sendable = capacity - fee_estimation

    return fee_estimation


def estimate_sendable_from_one_limiting_capacity(divisor, capacity, balance, number_of_hops_to_destination):
    """Estimates the max sendable amount in a path where the limiting capacity is assumed to be in a single trustline
    with given capacity, balance, and that is number_of_hops_to_destination away from the destination"""

    if divisor == 0:
        return capacity

    if number_of_hops_to_destination <= 0:
        return capacity

    imbalance = imbalance_generated(value=capacity, balance=balance)
    fee_estimation = estimate_max_fee_from_max_imbalance(divisor, imbalance)

    max_sendable = capacity - fee_estimation

    return estimate_sendable_from_one_limiting_capacity(divisor,
                                                        max_sendable,
                                                        balance,
                                                        number_of_hops_to_destination - 1)


def estimate_sendable(divisor, path_capacities, path_balances):
    """Estimates the max sendable amount in a path with given capacities and balances
    the estimated value returned is lower than the actual maximum sendable amount"""

    number_of_hops_to_destination = len(path_capacities)-1

    min_sendable = estimate_sendable_from_one_limiting_capacity(divisor,
                                                                path_capacities[len(path_capacities)-1],
                                                                path_balances[len(path_capacities)-1],
                                                                0)

    for i in range(number_of_hops_to_destination):

        print("i = ", i)
        print("capacity", path_capacities[i])

        current_sendable = estimate_sendable_from_one_limiting_capacity(divisor,
                                                                        path_capacities[i],
                                                                        path_balances[i],
                                                                        number_of_hops_to_destination)
        print("current_sendable", current_sendable)
        print("number_of_hops_to_dest", number_of_hops_to_destination)

        if current_sendable < min_sendable:
            min_sendable = current_sendable



        number_of_hops_to_destination -= 1

    return min_sendable