from typing import Tuple, Sequence, Optional

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker

from .order import Order
from eth_utils import force_bytes

Base = declarative_base()


class OrderORM(Base):  # type: ignore
    __tablename__ = 'orders'
    exchange_address = Column(String)
    maker_address = Column(String)
    taker_address = Column(String)
    maker_token = Column(String)
    taker_token = Column(String)
    fee_recipient = Column(String)
    maker_token_amount = Column(Integer)
    taker_token_amount = Column(Integer)
    filled_maker_token_amount = Column(Integer)
    filled_taker_token_amount = Column(Integer)
    cancelled_maker_token_amount = Column(Integer)
    cancelled_taker_token_amount = Column(Integer)
    price = Column(Float)
    maker_fee = Column(Integer)
    taker_fee = Column(Integer)
    expiration_timestamp_in_sec = Column(Integer)
    salt = Column(Integer)
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
            r=order.r.hex(),
            s=order.s.hex(),
            msg_hash=order.hash().hex()
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
            r=bytes.fromhex(self.r),
            s=bytes.fromhex(self.s)
        )


class OrderBookDB(object):

    def __init__(self, engine) -> None:
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        self.session = Session()

    def add_order(self, order: Order) -> None:
        order_orm = self.session.query(OrderORM).get(order.hash().hex())
        if order_orm is None:
            order_orm = OrderORM.from_order(order)
            self.session.add(order_orm)
            self.session.commit()

    def add_orders(self, orders: Sequence[Order]) -> None:
        for order in orders:
            self.add_order(order)

    def get_order_by_hash(self, order_hash: bytes) -> Optional[Order]:
        order_orm = self.session.query(OrderORM).get(order_hash.hex())
        if order_orm is None:
            return None
        return order_orm.to_order()

    def get_orderbook_by_tokenpair(self, token_pair: Tuple[str, str], desc_price: bool = False) -> Sequence[Order]:
        orders_orm = (self.session.query(OrderORM)
                      .filter(OrderORM.maker_token == token_pair[0],
                              OrderORM.taker_token == token_pair[1])
                      .order_by(OrderORM.price.desc() if desc_price else OrderORM.price,
                                OrderORM.expiration_timestamp_in_sec))
        return [order_orm.to_order() for order_orm in orders_orm]

    def delete_order_by_hash(self, order_hash: bytes) -> None:
        self.session.query(OrderORM).filter_by(msg_hash=order_hash.hex()).delete(synchronize_session=False)
        self.session.commit()

    def delete_orders_by_hash(self, order_hashes: Sequence[bytes]) -> None:
        for order_hash in order_hashes:
            self.session.query(OrderORM).filter_by(msg_hash=order_hash.hex()).delete(synchronize_session=False)
        self.session.commit()

    def delete_old_orders(self, timestamp: int) -> None:
        self.session.query(OrderORM).filter(OrderORM.expiration_timestamp_in_sec < timestamp)\
                                    .delete(synchronize_session=False)
        self.session.commit()

    def order_filled(self,
                     order_hash: bytes,
                     filled_maker_token_amount: int,
                     filled_taker_token_amount: int) -> None:
        # NOTE old version of web3.py returns bytes as string from contract, so we have to use force_bytes
        order_hash_bytes = force_bytes(order_hash)
        order_orm = self.session.query(OrderORM).filter_by(msg_hash=order_hash_bytes.hex()).first()
        if order_orm is not None:
            order_orm.filled_maker_token_amount += filled_maker_token_amount
            order_orm.filled_taker_token_amount += filled_taker_token_amount
            if order_orm.to_order().is_filled():
                self.session.delete(order_orm)
            self.session.commit()

    def order_cancelled(self,
                        order_hash: bytes,
                        cancelled_maker_token_amount: int,
                        cancelled_taker_token_amount: int) -> None:
        # NOTE old version of web3.py returns bytes as string from contract, so we have to use force_bytes
        order_hash_bytes = force_bytes(order_hash)
        order_orm = self.session.query(OrderORM).filter_by(msg_hash=order_hash_bytes.hex()).first()
        if order_orm is not None:
            order_orm.cancelled_maker_token_amount += cancelled_maker_token_amount
            order_orm.cancelled_taker_token_amount += cancelled_taker_token_amount
            if order_orm.to_order().is_filled():
                self.session.delete(order_orm)
            self.session.commit()
