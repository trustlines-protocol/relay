def imbalance_fee(divisor, pre_balance, value):
    if divisor == 0:
        return 0
    imbalance_generated = value
    if pre_balance > 0:
        imbalance_generated = value - pre_balance
        if imbalance_generated <= 0:
            return 0
    return (imbalance_generated // divisor) + 1  # minimum fee is 1


def new_balance(divisor, pre_balance, value):
    fee = imbalance_fee(divisor, pre_balance, value)
    return pre_balance - value - fee


def estimate_fees_from_capacity(divisor, min_capacity, path_capacities):
        """
        Gives an upper bound on the fees for a max capacity transfer
        The "imbalance_fee" function not being bijective, only an estimate of the fees can be found from "value + fee"
        Now I actually believe I find the exact value / the best estimate.

        Args:
            divisor: the divisor used to calculate imbalance fees
            min_capacity: the maximum capacity of a path (the minimum capacity of path_capacities)
            path_capacities: a list of the (ordered) capacities of the vertices along the path

        Returns:
            returns the value of the fees
        """

        if divisor == 0:
            return 0

        hops = len(path_capacities)
        fees = 0
        for i in range(hops):
            capacity = min(path_capacities[i], min_capacity+fees)
            fees += int((1+capacity/divisor)/(1+1/divisor))

        return fees
