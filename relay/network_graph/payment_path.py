from enum import Enum
from typing import List

import attr


class FeePayer(Enum):
    SENDER = "sender"
    RECEIVER = "receiver"


@attr.s(auto_attribs=True)
class PaymentPath:
    fee: int
    path: List
    value: int
    fee_payer: FeePayer
