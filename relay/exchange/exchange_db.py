from typing import Tuple, Sequence, Optional

import hexbytes
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, BigInteger
from sqlalchemy.orm import sessionmaker
from eth_utils.hexadecimal import remove_0x_prefix

from .order import Order
from relay.concurrency_utils import synchronized


Base = declarative_base()


class OrderORM(Base):  # type: ignore
    __tablename__ = 'orders'
    exchange_address = Column(String)
    maker_address = Column(String)
    taker_address = Column(String)
    maker_token = Column(String)
    taker_token = Column(String)
    fee_recipient = Column(String)
    maker_token_amount = Column(BigInteger)
    taker_token_amount = Column(BigInteger)
    filled_maker_token_amount = Column(BigInteger)
    filled_taker_token_amount = Column(BigInteger)
    cancelled_maker_token_amount = Column(BigInteger)
    cancelled_taker_token_amount = Column(BigInteger)
    price = Column(Float)
    maker_fee = Column(Integer)
    taker_fee = Column(Integer)
    expiration_timestamp_in_sec = Column(BigInteger)
    salt = Column(BigInteger)
    v = Column(Integer)
    r = Column(String)
    s = Column(String)
    msg_hash = Column(String, primary_key=True)

    @classmethod
    def from_order(cls, order: Order) -> 'OrderORM':
        return cls(
            exchange_address=order.exchange_address,
            maker_address=order.maker_address,
            taker_address=order.taker_address,
            maker_token=order.maker_token,
            taker_token=order.taker_token,
            fee_recipient=order.fee_recipient,
            maker_token_amount=order.maker_token_amount,
            taker_token_amount=order.taker_token_amount,
            filled_maker_token_amount=order.filled_maker_token_amount,
            filled_taker_token_amount=order.filled_taker_token_amount,
            cancelled_maker_token_amount=order.cancelled_maker_token_amount,
            cancelled_taker_token_amount=order.cancelled_taker_token_amount,
            price=order.price,
            maker_fee=order.maker_fee,
            taker_fee=order.taker_fee,
            expiration_timestamp_in_sec=order.expiration_timestamp_in_sec,
            salt=order.salt,
            v=order.v,
            r=remove_0x_prefix(order.r.hex()),  # remove 0x to keep backwards compatibility
            s=remove_0x_prefix(order.s.hex()),  # remove 0x to keep backwards compatibility
            msg_hash=remove_0x_prefix(order.hash().hex())  # remove 0x to keep backwards compatibility
        )

    def to_order(self) -> Order:
        return Order(
            exchange_address=self.exchange_address,
            maker_address=self.maker_address,
            taker_address=self.taker_address,
            maker_token=self.maker_token,
            taker_token=self.taker_token,
            fee_recipient=self.fee_recipient,
            maker_token_amount=self.maker_token_amount,
            taker_token_amount=self.taker_token_amount,
            filled_maker_token_amount=self.filled_maker_token_amount,
            filled_taker_token_amount=self.filled_taker_token_amount,
            cancelled_maker_token_amount=self.cancelled_maker_token_amount,
            cancelled_taker_token_amount=self.cancelled_taker_token_amount,
            maker_fee=self.maker_fee,
            taker_fee=self.taker_fee,
            expiration_timestamp_in_sec=self.expiration_timestamp_in_sec,
            salt=self.salt,
            v=self.v,
            r=hexbytes.HexBytes(self.r),
            s=hexbytes.HexBytes(self.s)
        )


class OrderBookDB(object):

    def __init__(self, engine) -> None:
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        self.session = Session()

    @synchronized
    def add_order(self, order: Order) -> None:
        # remove 0x to keep backwards compatibility
        order_orm = self.session.query(OrderORM).get(remove_0x_prefix(order.hash().hex()))
        if order_orm is None:
            order_orm = OrderORM.from_order(order)
            self.session.add(order_orm)
            self.session.commit()

    @synchronized
    def add_orders(self, orders: Sequence[Order]) -> None:
        for order in orders:
            self.add_order(order)

    @synchronized
    def get_order_by_hash(self, order_hash: hexbytes.HexBytes) -> Optional[Order]:
        # remove 0x to keep backwards compatibility
        order_orm = self.session.query(OrderORM).get(remove_0x_prefix(order_hash.hex()))
        if order_orm is None:
            return None
        return order_orm.to_order()

    @synchronized
    def get_orderbook_by_tokenpair(self, token_pair: Tuple[str, str], desc_price: bool = False) -> Sequence[Order]:
        orders_orm = (self.session.query(OrderORM)
                      .filter(OrderORM.maker_token == token_pair[0],
                              OrderORM.taker_token == token_pair[1])
                      .order_by(OrderORM.price.desc() if desc_price else OrderORM.price,
                                OrderORM.expiration_timestamp_in_sec))
        return [order_orm.to_order() for order_orm in orders_orm]

    @synchronized
    def get_orders(self,
                   filter_exchange_address: str = None,
                   filter_token_address: str = None,
                   filter_maker_token_address: str = None,
                   filter_taker_token_address: str = None,
                   filter_trader_address: str = None,
                   filter_maker_address: str = None,
                   filter_taker_address: str = None,
                   filter_fee_recipient_address: str = None) -> Sequence[Order]:
        orders_orm = self.session.query(OrderORM)

        if (filter_exchange_address is not None):
            orders_orm.filter(OrderORM.exchange_address == filter_exchange_address)
        if (filter_token_address is not None):
            orders_orm.filter((OrderORM.maker_token == filter_token_address) |
                              (OrderORM.taker_token == filter_token_address))
        if (filter_maker_token_address is not None):
            orders_orm.filter(OrderORM.maker_token == filter_maker_token_address)
        if (filter_taker_token_address is not None):
            orders_orm.filter(OrderORM.taker_token == filter_taker_token_address)
        if (filter_trader_address is not None):
            orders_orm.filter((OrderORM.maker_address == filter_trader_address) |
                              (OrderORM.taker_address == filter_trader_address))
        if (filter_maker_address is not None):
            orders_orm.filter(OrderORM.maker_address == filter_maker_address)
        if (filter_taker_address is not None):
            orders_orm.filter(OrderORM.taker_address == filter_taker_address)
        if (filter_fee_recipient_address is not None):
            orders_orm.filter(OrderORM.fee_recipient == filter_fee_recipient_address)

        return [order_orm.to_order() for order_orm in orders_orm]

    @synchronized
    def delete_order_by_hash(self, order_hash: hexbytes.HexBytes) -> None:
        # remove 0x to keep backwards compatibility
        self.session.query(OrderORM).filter_by(msg_hash=remove_0x_prefix(order_hash.hex())).delete(
            synchronize_session=False)
        self.session.commit()

    @synchronized
    def delete_orders_by_hash(self, order_hashes: Sequence[hexbytes.HexBytes]) -> None:
        for order_hash in order_hashes:
            # remove 0x to keep backwards compatibility
            self.session.query(OrderORM).filter_by(msg_hash=remove_0x_prefix(order_hash.hex())).delete(
                synchronize_session=False)
        self.session.commit()

    @synchronized
    def delete_old_orders(self, timestamp: int) -> None:
        self.session.query(OrderORM).filter(OrderORM.expiration_timestamp_in_sec < timestamp)\
                                    .delete(synchronize_session=False)
        self.session.commit()

    @synchronized
    def order_filled(self,
                     order_hash: hexbytes.HexBytes,
                     filled_maker_token_amount: int,
                     filled_taker_token_amount: int) -> None:
        # remove 0x to keep backwards compatibility
        order_orm = self.session.query(OrderORM).filter_by(msg_hash=remove_0x_prefix(order_hash.hex())).first()
        if order_orm is not None:
            order_orm.filled_maker_token_amount += filled_maker_token_amount
            order_orm.filled_taker_token_amount += filled_taker_token_amount
            if order_orm.to_order().is_filled():
                self.session.delete(order_orm)
            self.session.commit()

    @synchronized
    def order_cancelled(self,
                        order_hash: hexbytes.HexBytes,
                        cancelled_maker_token_amount: int,
                        cancelled_taker_token_amount: int) -> None:
        # remove 0x to keep backwards compatibility
        order_orm = self.session.query(OrderORM).filter_by(msg_hash=remove_0x_prefix(order_hash.hex())).first()
        if order_orm is not None:
            order_orm.cancelled_maker_token_amount += cancelled_maker_token_amount
            order_orm.cancelled_taker_token_amount += cancelled_taker_token_amount
            if order_orm.to_order().is_filled():
                self.session.delete(order_orm)
            self.session.commit()
