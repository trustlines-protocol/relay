import pytest

from relay.blockchain.currency_network_events import (
    TransferEventType,
    TrustlineRequestEventType,
    TrustlineUpdateEventType,
)


@pytest.fixture()
def web3_event():
    return {
        "blockNumber": 5,
        "transactionHash": "0x1234",
        "address": "0x12345",
        "logIndex": 0,
        "blockHash": "0x123456",
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
def web3_event_trustline_request(web3_event):
    web3_event.update(
        {
            "args": {
                "_creditor": "0x123",
                "_debtor": "0x1234",
                "_creditlineGiven": 50,
                "_creditlineReceived": 100,
                "_isFrozen": True,
            },
            "event": TrustlineRequestEventType,
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
