import hexbytes
import pytest

from relay.blockchain.currency_network_events import (
    TransferEvent,
    TransferEventType,
    TrustlineUpdateEvent,
    TrustlineUpdateEventType,
)
from relay.blockchain.events import BlockchainEvent


@pytest.fixture()
def web3_event():
    return {
        "blockNumber": 5,
        "blockHash": "0xd74c3e8bdb19337987b987aee0fa48ed43f8f2318edfc84e3a8643e009592a68",
        "transactionHash": "0x1234",
        "address": "0x12345",
        "event": "TestEvent",
        "logIndex": 2,
    }


@pytest.fixture()
def web3_event_trustline_update(web3_event):
    web3_event.update(
        {
            "args": {
                "_creditor": "0x123",
                "_debtor": "0x1234",
                "_creditlineGiven": 50,
                "_creditlineReceived": 100,
                "_isFrozen": True,
            },
            "event": TrustlineUpdateEventType,
        }
    )
    return web3_event


@pytest.fixture()
def web3_event_transfer(web3_event, test_extra_data):
    web3_event.update(
        {
            "args": {
                "_from": "0x123",
                "_to": "0x1234",
                "_value": 150,
                "_extraData": test_extra_data,
            },
            "event": TransferEventType,
        }
    )
    return web3_event


def test_blockchain_event(web3_event):
    event = BlockchainEvent(web3_event, 10, 123456)

    assert event.blocknumber == 5
    assert event.transaction_id == hexbytes.HexBytes("0x1234")
    assert event.type == "TestEvent"
    assert event.id == hexbytes.HexBytes(
        "0x45cc770036e3baccdccae4a22fe6bf66f52d29e97a6f95798966d920bf6cc7ab"
    )


def test_trustline_update_event(web3_event_trustline_update):
    event = TrustlineUpdateEvent(web3_event_trustline_update, 10, 123456, "0x1234")

    assert event.from_ == "0x123"
    assert event.to == "0x1234"
    assert event.user == "0x1234"
    assert event.counter_party == "0x123"
    assert event.creditline_given == 50
    assert event.creditline_received == 100
    assert event.is_frozen is True
    assert event.status == "confirmed"
    assert event.direction == "received"


def test_transfer_event(web3_event_transfer, test_extra_data):
    event = TransferEvent(web3_event_transfer, 6, 123456, "0x123")

    assert event.from_ == "0x123"
    assert event.to == "0x1234"
    assert event.user == "0x123"
    assert event.counter_party == "0x1234"
    assert event.value == 150
    assert event.status == "pending"
    assert event.direction == "sent"
    assert event.extra_data == test_extra_data
