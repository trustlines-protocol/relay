from typing import List
import attr


@attr.s(auto_attribs=True)
class PaymentPath:
    fee: int
    path: List
    value: int
    sender_pays_fees: bool = attr.ib(default=True)
    estimated_gas: int = attr.ib(default=None)
