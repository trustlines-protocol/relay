from relay.blockchain.currency_network_events import TransferEvent, TrustlineUpdateEvent


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
