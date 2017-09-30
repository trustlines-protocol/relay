

def imbalance_fee(factor, pre_balance, value):
    imbalance_generated = value
    if pre_balance > 0:
        imbalance_generated = value - pre_balance
        if imbalance_generated <= 0:
            return 0
    return (imbalance_generated // factor) + 1  # minimum fee is 1


def new_balance(factor, pre_balance, value):
    fee = imbalance_fee(factor, pre_balance, value)
    return pre_balance - value - fee
