from collections import namedtuple

import hexbytes
from eth_utils import is_checksum_address

from relay.signing import keccak256, eth_sign, eth_validate


EcSignature = namedtuple('EcSignature', 'v r s')


class Order(object):

    def __init__(
        self,
        exchange_address: str,
        maker_address: str,
        taker_address: str,
        maker_token: str,
        taker_token: str,
        fee_recipient: str,
        maker_token_amount: int,
        taker_token_amount: int,
        maker_fee: int,
        taker_fee: int,
        expiration_timestamp_in_sec: int,
        salt: int,
        v: int,
        r: hexbytes.HexBytes,
        s: hexbytes.HexBytes,
        filled_maker_token_amount: int = 0,
        filled_taker_token_amount: int = 0,
        cancelled_maker_token_amount: int = 0,
        cancelled_taker_token_amount: int = 0
    ) -> None:
        self.exchange_address = exchange_address
        self.maker_address = maker_address
        self.taker_address = taker_address
        self.maker_token = maker_token
        self.taker_token = taker_token
        self.fee_recipient = fee_recipient
        self.maker_token_amount = maker_token_amount
        self.taker_token_amount = taker_token_amount
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.expiration_timestamp_in_sec = expiration_timestamp_in_sec
        self.salt = salt
        self.v = v
        self.r = r
        self.s = s
        self.filled_maker_token_amount = filled_maker_token_amount
        self.filled_taker_token_amount = filled_taker_token_amount
        self.cancelled_maker_token_amount = cancelled_maker_token_amount
        self.cancelled_taker_token_amount = cancelled_taker_token_amount

    @property
    def price(self) -> float:
        return self.taker_token_amount / self.maker_token_amount

    @property
    def available_maker_token_amount(self) -> float:
        return self.maker_token_amount - self.filled_maker_token_amount - self.cancelled_maker_token_amount

    @property
    def available_taker_token_amount(self) -> float:
        return self.taker_token_amount - self.filled_taker_token_amount - self.cancelled_taker_token_amount

    @property
    def ec_signature(self):
        return EcSignature(self.v, self.r, self. s)

    def validate(self) -> bool:
        return self.validate_signature() and self.validate_addresses()

    def validate_signature(self) -> bool:
        return eth_validate(self.hash(), (self.v, self.r, self.s), self.maker_address)

    def validate_addresses(self) -> bool:
        for address in [self.exchange_address, self.maker_token, self.taker_token, self.fee_recipient]:
            if not is_checksum_address(address):
                return False
        return True

    def is_expired(self, current_timestamp_in_sec: int) -> bool:
        return current_timestamp_in_sec > self.expiration_timestamp_in_sec

    def is_filled(self) -> bool:
        return self.available_maker_token_amount <= 0 or self.available_taker_token_amount <= 0

    def hash(self) -> hexbytes.HexBytes:
        return hexbytes.HexBytes(keccak256(
            self.exchange_address,
            self.maker_address,
            self.taker_address,
            self.maker_token,
            self.taker_token,
            self.fee_recipient,
            self.maker_token_amount,
            self.taker_token_amount,
            self.maker_fee,
            self.taker_fee,
            self.expiration_timestamp_in_sec,
            self.salt
        ))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Order):
            return self.hash() == other.hash()
        else:
            return False


class SignableOrder(Order):
    def __init__(
            self,
            exchange_address: str,
            maker_address: str,
            taker_address: str,
            maker_token: str,
            taker_token: str,
            fee_recipient: str,
            maker_token_amount: int,
            taker_token_amount: int,
            maker_fee: int,
            taker_fee: int,
            expiration_timestamp_in_sec: int,
            salt: int
    ) -> None:
        super().__init__(exchange_address,
                         maker_address,
                         taker_address,
                         maker_token,
                         taker_token,
                         fee_recipient,
                         maker_token_amount,
                         taker_token_amount,
                         maker_fee,
                         taker_fee,
                         expiration_timestamp_in_sec,
                         salt,
                         v=0,
                         r=hexbytes.HexBytes(b''),
                         s=hexbytes.HexBytes(b''))

    def sign(self, key) -> None:
        v, r, s = eth_sign(self.hash(), key)
        self.v = v
        self.r = hexbytes.HexBytes(r)
        self.s = hexbytes.HexBytes(s)
