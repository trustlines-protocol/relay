import pytest

from sqlalchemy import create_engine

from relay.pushservice.client_token_db import ClientTokenDB, ClientTokenAlreadyExistsException


@pytest.fixture()
def client_token_db():
    return ClientTokenDB(create_engine('sqlite:///:memory:'))


def test_add_client_token(client_token_db: ClientTokenDB):
    client_token_db.add_client_token('0x123', 'token')
    assert client_token_db.get_client_tokens('0x123') == ['token']


def test_add_multiple_client_token(client_token_db: ClientTokenDB):
    client_token_db.add_client_token('0x123', 'token1')
    client_token_db.add_client_token('0x123', 'token2')
    client_token_db.add_client_token('0x123', 'token3')
    assert set(client_token_db.get_client_tokens('0x123')) == {'token1', 'token2', 'token3'}


def test_cannot_add_same_token_twice(client_token_db: ClientTokenDB):
    client_token_db.add_client_token('0x123', 'token')
    with pytest.raises(ClientTokenAlreadyExistsException):
        client_token_db.add_client_token('0x123', 'token')
    assert client_token_db.get_client_tokens('0x123') == ['token']


def test_delete_token(client_token_db: ClientTokenDB):
    client_token_db.add_client_token('0x123', 'token')
    client_token_db.delete_client_token('0x123', 'token')
    assert client_token_db.get_client_tokens('0x123') == []


def test_delete_non_existent_token(client_token_db: ClientTokenDB):
    client_token_db.delete_client_token('0x123', 'token')
    assert client_token_db.get_client_tokens('0x123') == []


def test_get_client_tokens(client_token_db: ClientTokenDB):
    client_token_db.add_client_token('0x123', 'token1')
    client_token_db.add_client_token('0x124', 'token2')
    client_token_db.add_client_token('0x125', 'token3')
    assert client_token_db.get_client_tokens('0x124') == ['token2']


def test_all_tokens(client_token_db: ClientTokenDB):
    client_token_db.add_client_token('0x123', 'token1')
    client_token_db.add_client_token('0x124', 'token2')
    client_token_db.add_client_token('0x125', 'token3')
    assert set(client_token_db.get_all_client_tokens()) == {('0x123', 'token1'),
                                                            ('0x124', 'token2'),
                                                            ('0x125', 'token3')}
