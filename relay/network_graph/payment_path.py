from typing import List
import attr
from enum import Enum


class FeePayer(Enum):
    SENDER = "sender"
    RECEIVER = "receiver"


@attr.s(auto_attribs=True)
class PaymentPath:
    fee: int
    path: List
    value: int
    fee_payer: FeePayer
    estimated_gas: int = attr.ib(default=None)
