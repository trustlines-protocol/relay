def imbalance_fee(factor, pre_balance, value):
    if factor == 0:
        return 0
    imbalance_generated = value
    if pre_balance > 0:
        imbalance_generated = value - pre_balance
        if imbalance_generated <= 0:
            return 0
    return (imbalance_generated // factor) + 1  # minimum fee is 1


def new_balance(factor, pre_balance, value):
    fee = imbalance_fee(factor, pre_balance, value)
    return pre_balance - value - fee


def estimate_fees_from_capacity(factor, capacity, hops, previous_hops_value=0):
        """
        Gives an upper bound on the fees for a max capacity transfer with n hops
        The "imbalance_fee" function not being bijective, only an estimate of the fees can be found from "value + fee"
        uses recursion to find the closest estimate

        Args:
            factor: the divisor used to calculate imbalance fees (not actually a factor)
            capacity: the maximum capacity of a path
            hops: the number of hops in the path
            previous_hops_value: the value of the fees for the previous hop

        Returns:
            returns the value of the fees
        """
        if factor == 0:
            return 0

        if hops == 1:
            return (capacity + previous_hops_value)//factor + 1 + previous_hops_value
        else:
            return estimate_fees_from_capacity(factor, capacity, hops-1, previous_hops_value + 1 +
                                               (capacity + previous_hops_value)//factor)
