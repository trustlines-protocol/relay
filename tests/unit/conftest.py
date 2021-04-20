import pytest

from relay.blockchain.currency_network_events import (
    TransferEventType,
    TrustlineRequestCancelEventType,
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
    trustline_update_event = web3_event.copy()
    trustline_update_event.update(
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
    return trustline_update_event


@pytest.fixture()
def web3_event_trustline_request(web3_event):
    trustline_request_event = web3_event.copy()
    trustline_request_event.update(
        {
            "args": {
                "_creditor": "0x123",
                "_debtor": "0x1234",
                "_creditlineGiven": 50,
                "_creditlineReceived": 100,
                "_isFrozen": True,
                "_transfer": 10,
            },
            "event": TrustlineRequestEventType,
        }
    )
    return trustline_request_event


@pytest.fixture()
def web3_event_trustline_request_cancel(web3_event):
    trustline_request_cancel_event = web3_event.copy()
    trustline_request_cancel_event.update(
        {
            "args": {"_initiator": "0x123", "_counterparty": "0x1234"},
            "event": TrustlineRequestCancelEventType,
        }
    )
    return trustline_request_cancel_event


@pytest.fixture()
def web3_event_transfer(web3_event, test_extra_data):
    trustlines_transfer_event = web3_event.copy()
    trustlines_transfer_event.update(
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
    return trustlines_transfer_event
