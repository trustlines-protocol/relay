SECONDS_PER_YEAR = 60 * 60 * 24 * 365
INTERESTS_DECIMALS = 2


def calculate_interests(balance: int,
                        internal_interest_rate: int,
                        delta_time_in_seconds: int,
                        highest_order: int = 15) -> int:
    intermediate_order = balance
    interests = 0
    # Calculate compound interests using taylor approximation
    for order in range(1, highest_order + 1):
        intermediate_order = int(intermediate_order * internal_interest_rate * delta_time_in_seconds /
                                 (SECONDS_PER_YEAR * 100 * 10 ** INTERESTS_DECIMALS * order))

        if intermediate_order == 0:
            break
        interests += intermediate_order

    return interests


def balance_with_interests(balance: int,
                           internal_interest_rate_positive_balance: int,
                           internal_interest_rate_negative_balance: int,
                           delta_time_in_seconds: int) -> int:
    if balance > 0:
        interest = calculate_interests(balance, internal_interest_rate_positive_balance, delta_time_in_seconds)
    else:
        interest = calculate_interests(balance, internal_interest_rate_negative_balance, delta_time_in_seconds)
    total = balance + interest
    assert isinstance(total, int)
    return total
