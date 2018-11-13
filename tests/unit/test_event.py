import pytest

from relay.blockchain.currency_network_events import (
    TrustlineUpdateEvent,
    TransferEvent,
    TransferEventType,
    TrustlineUpdateEventType,
)


@pytest.fixture()
def web3_event():
    return {
        'blockNumber': 5,
        'transactionHash': '0x1234',
        'address': '0x12345'
    }


@pytest.fixture()
def web3_event_trustline_update(web3_event):
    web3_event.update({
        'args': {
            '_creditor': '0x123',
            '_debtor': '0x1234',
            '_creditlineGiven': 50,
            '_creditlineReceived': 100
        },
        'event': TrustlineUpdateEventType
    })
    return web3_event


@pytest.fixture()
def web3_event_transfer(web3_event):
    web3_event.update({
        'args': {
            '_from': '0x123',
            '_to': '0x1234',
            '_value': 150,
        },
        'event': TransferEventType
    })
    return web3_event


def test_trustline_update_event(web3_event_trustline_update):
    event = TrustlineUpdateEvent(web3_event_trustline_update, 10, 123456, '0x1234')

    assert event.from_ == '0x123'
    assert event.to == '0x1234'
    assert event.user == '0x1234'
    assert event.counter_party == '0x123'
    assert event.creditline_given == 50
    assert event.creditline_received == 100
    assert event.status == 'confirmed'
    assert event.direction == 'received'


def test_transfer_event(web3_event_transfer):
    event = TransferEvent(web3_event_transfer, 6, 123456, '0x123')

    assert event.from_ == '0x123'
    assert event.to == '0x1234'
    assert event.user == '0x123'
    assert event.counter_party == '0x1234'
    assert event.value == 150
    assert event.status == 'pending'
    assert event.direction == 'sent'
