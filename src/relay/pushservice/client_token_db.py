from collections import namedtuple
from contextlib import contextmanager
from typing import Iterable

from sqlalchemy import Column, String
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class TokenMappingORM(Base):  # type: ignore
    __tablename__ = "client_token"
    user_address = Column(String, index=True, primary_key=True)
    client_token = Column(String, primary_key=True)


class ClientTokenDBException(Exception):
    pass


class ClientTokenAlreadyExistsException(ClientTokenDBException):
    pass


TokenMapping = namedtuple("TokenMapping", ["user_address", "client_token"])


class ClientTokenDB:
    def __init__(self, engine) -> None:
        self._make_session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)

    @contextmanager
    def session(self):
        """Provide a transactional scope around a series of operations."""
        session = self._make_session()
        try:
            yield session
            session.commit()
        except BaseException:
            session.rollback()
            raise
        finally:
            session.close()

    def get_client_tokens(self, user_address: str) -> Iterable[str]:
        with self.session() as session:
            return [
                client_token
                for (client_token,) in session.query(TokenMappingORM.client_token)
                .filter(TokenMappingORM.user_address == user_address)
                .all()
            ]

    def get_all_client_tokens(self) -> Iterable[TokenMapping]:
        with self.session() as session:
            return [
                TokenMapping(
                    token_mapping_orm.user_address, token_mapping_orm.client_token
                )
                for token_mapping_orm in (session.query(TokenMappingORM).all())
            ]

    def add_client_token(self, user_address: str, client_token: str) -> None:
        """
        Adds a client token for the given user address

        user address and client token are not checked to be valid, this needs to be ensured by the user

        Raises:
        ClientTokenAlreadyExistsException: If the combination of user_address and client_token already exists
        """
        with self.session() as session:
            tokenMappingOrm = TokenMappingORM(
                user_address=user_address, client_token=client_token
            )
            try:
                session.add(tokenMappingOrm)
                session.commit()
            except IntegrityError as e:
                raise ClientTokenAlreadyExistsException from e

    def delete_client_token(self, user_address: str, client_token: str) -> None:
        """Deletes a client token from the given user address"""
        with self.session() as session:
            session.query(TokenMappingORM).filter(
                TokenMappingORM.user_address == user_address,
                TokenMappingORM.client_token == client_token,
            ).delete()
