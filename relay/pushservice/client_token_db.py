from typing import Iterable
from collections import namedtuple

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

Base = declarative_base()


class TokenMappingORM(Base):  # type: ignore
    __tablename__ = 'client_token'
    user_address = Column(String, index=True, primary_key=True)
    client_token = Column(String, primary_key=True)


class ClientTokenDBException(Exception):
    pass


class ClientTokenAlreadyExistsException(ClientTokenDBException):
    pass


TokenMapping = namedtuple('TokenMapping', ['user_address', 'client_token'])


class ClientTokenDB:

    def __init__(self, engine) -> None:
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        self.session = Session()

    def get_client_tokens(self, user_address: str) -> Iterable[str]:
        return [client_token for (client_token,) in self.session.query(TokenMappingORM.client_token)
                .filter(TokenMappingORM.user_address == user_address).all()]

    def get_all_client_tokens(self) -> Iterable[TokenMapping]:
        return [TokenMapping(token_mapping_orm.user_address, token_mapping_orm.client_token) for token_mapping_orm in
                (self.session.query(TokenMappingORM).all())]

    def add_client_token(self, user_address: str, client_token: str) -> None:
        """
        Adds a client token for the given user address

        user address and client token are not checked to be valid, this needs to be ensured by the user

        Raises:
        ClientTokenAlreadyExistsException: If the combination of user_address and client_token already exists
        """
        tokenMappingOrm = TokenMappingORM(user_address=user_address, client_token=client_token)
        try:
            self.session.add(tokenMappingOrm)
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise ClientTokenAlreadyExistsException from e

    def delete_client_token(self, user_address: str, client_token: str) -> None:
        """Deletes a client token from the given user address"""
        self.session.query(TokenMappingORM).filter(TokenMappingORM.user_address == user_address,
                                                   TokenMappingORM.client_token == client_token).delete()
        self.session.commit()
