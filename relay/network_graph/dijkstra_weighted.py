from typing import List
import attr


@attr.s(auto_attribs=True)
class PaymentPath:
    fee: int
    path: List
    value: int
    estimated_gas: int = attr.ib(default=None)
