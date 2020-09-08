import json
import time

import firebase_admin
import pytest
from firebase_admin import messaging

from relay.blockchain.currency_network_events import (
    TransferEvent,
    TrustlineRequestCancelEvent,
    TrustlineRequestEvent,
    TrustlineUpdateEvent,
)
from relay.events import MessageEvent
from relay.pushservice.pushservice import (
    FirebaseRawPushService,
    _build_data_message,
    _build_data_prop,
)

from .utils import MockAdapter, MockCredential

requestMessagePayload = (
    '{"type":"PaymentRequest","networkAddress":"0x12657128d7fa4291647eC3b0147E5fA6EebD388A",'
    '"from":"0xB6cD40e87d1ED3eCd455cDa0B6EA9FD56F83f0a7",'
    '"to":"0xE85bd548b2C961A2385628dcbBcc9A2E480dD925","amount":{"decimals":8,"raw":"1000000000",'
    '"value":"10"},"subject":"test subject","id":"0x5d57fabcc8b6055b",'
    '"counterParty":"0xB6cD40e87d1ED3eCd455cDa0B6EA9FD56F83f0a7","direction":"received",'
    '"user":"0xE85bd548b2C961A2385628dcbBcc9A2E480dD925"} '
)

requestDeclineMessagePayload = (
    '{"type":"PaymentRequestDecline","id":"0x5d57fabcc8b6055b",'
    '"subject":"decline subject"} '
)

payment_request_message_event = MessageEvent(
    message=requestMessagePayload, type="PaymentRequest", timestamp=int(time.time())
)

payment_request_decline_message_event = MessageEvent(
    message=requestDeclineMessagePayload,
    type="PaymentRequestDecline",
    timestamp=int(time.time()),
)

cred = MockCredential()
all_options = {"projectId": "explicit-project-id"}
admin_app = firebase_admin.initialize_app(cred, all_options)

_DEFAULT_RESPONSE = json.dumps({"name": "message-id"})


def _instrument_messaging_service(app, status=200, payload=_DEFAULT_RESPONSE):
    fcm_service = messaging._get_messaging_service(app)
    recorder = []
    fcm_service._client.session.mount(
        "https://fcm.googleapis.com", MockAdapter(payload, status, recorder)
    )
    return fcm_service, recorder


@pytest.fixture()
def raw_push_service():
    return FirebaseRawPushService(app=admin_app)


@pytest.fixture()
def recorder(raw_push_service):
    _, recorder = _instrument_messaging_service(app=raw_push_service._app)
    return recorder


def assert_body_has_correct_payload(recorder, events):
    assert len(recorder) == len(events)

    for i, event in enumerate(events):
        body = {
            "message": messaging._MessagingService.encode_message(
                _build_data_message(client_token="token", event=event)
            )
        }
        assert json.loads(recorder[i].body.decode()) == body


def test_send_on_blockchain_event(
    raw_push_service,
    recorder,
    web3_event_transfer,
    web3_event_trustline_request,
    web3_event_trustline_request_cancel,
    web3_event_trustline_update,
):
    events = [
        TransferEvent(
            web3_event=web3_event_transfer,
            current_blocknumber=6,
            timestamp=123456,
            user="0x321",
        ),
        TrustlineRequestEvent(
            web3_event=web3_event_trustline_request,
            current_blocknumber=7,
            timestamp=234567,
            user="0x321",
        ),
        TrustlineRequestCancelEvent(
            web3_event=web3_event_trustline_request_cancel,
            current_blocknumber=8,
            timestamp=345678,
            user="0x321",
        ),
        TrustlineUpdateEvent(
            web3_event=web3_event_trustline_update,
            current_blocknumber=9,
            timestamp=456789,
            user="0x321",
        ),
    ]

    for event in events:
        raw_push_service.send_event(client_token="token", event=event)

    assert_body_has_correct_payload(recorder, events)


def test_send_on_non_blockchain_event(raw_push_service, recorder):
    message_events = [
        payment_request_message_event,
        payment_request_decline_message_event,
    ]

    for message_event in message_events:
        raw_push_service.send_event(client_token="token", event=message_event)

    assert_body_has_correct_payload(recorder, message_events)


def test_build_data_prop_trustline_update(web3_event_trustline_update):
    event = TrustlineUpdateEvent(web3_event_trustline_update, 10, 123456, "0x1234")
    data = _build_data_prop(event)
    assert data == {
        "blockHash": "0x123456",
        "blockNumber": "5",
        "eventType": "TrustlineUpdate",
        "logIndex": "0",
        "transactionHash": "0x1234",
    }


def test_build_data_prop_trustline_transfer(web3_event_transfer):
    event = TransferEvent(
        web3_event=web3_event_transfer,
        current_blocknumber=6,
        timestamp=123456,
        user="0x321",
    )

    data = _build_data_prop(event)
    assert data == {
        "blockHash": "0x123456",
        "blockNumber": "5",
        "eventType": "Transfer",
        "logIndex": "0",
        "transactionHash": "0x1234",
    }


def test_build_data_prop_trustline_request_event(web3_event_trustline_request):
    event = TrustlineRequestEvent(
        web3_event=web3_event_trustline_request,
        current_blocknumber=6,
        timestamp=123456,
        user="0x321",
    )

    data = _build_data_prop(event)
    assert data == {
        "blockHash": "0x123456",
        "eventType": "TrustlineUpdateRequest",
        "logIndex": "0",
        "blockNumber": "5",
        "transactionHash": "0x1234",
    }


def test_build_data_prop_trustline_request_cancel_event(
    web3_event_trustline_request_cancel,
):
    event = TrustlineRequestCancelEvent(
        web3_event=web3_event_trustline_request_cancel,
        current_blocknumber=6,
        timestamp=123456,
        user="0x321",
    )

    data = _build_data_prop(event)
    assert data == {
        "blockHash": "0x123456",
        "eventType": "TrustlineUpdateCancel",
        "logIndex": "0",
        "blockNumber": "5",
        "transactionHash": "0x1234",
    }


def test_build_data_prop_payment_request():
    payment_request_event = MessageEvent(
        message=requestMessagePayload, type="PaymentRequest", timestamp=int(time.time())
    )

    data = _build_data_prop(payment_request_event)

    assert data == {"message": requestMessagePayload, "eventType": "PaymentRequest"}


def test_build_data_prop_payment_request_decline():
    payment_request_decline_event = MessageEvent(
        message=requestDeclineMessagePayload,
        type="PaymentRequestDecline",
        timestamp=int(time.time()),
    )

    data = _build_data_prop(payment_request_decline_event)

    assert data == {
        "message": requestDeclineMessagePayload,
        "eventType": "PaymentRequestDecline",
    }


def test_build_firebase_data_message(web3_event_trustline_request):
    request_event = TrustlineRequestEvent(
        web3_event=web3_event_trustline_request,
        current_blocknumber=6,
        timestamp=123456,
        user="0x321",
    )
    data = _build_data_prop(request_event)

    message = _build_data_message(client_token="token", event=request_event)

    assert message.data["blockHash"] == data["blockHash"]
    assert message.data["eventType"] == data["eventType"]
    assert message.data["blockNumber"] == data["blockNumber"]
    assert message.data["logIndex"] == data["logIndex"]
    assert message.data["transactionHash"] == data["transactionHash"]
    assert message.token == "token"
    assert message.android.priority == "high"
    assert message.apns.payload.aps.content_available == 1
    assert message.apns.headers["apns-priority"] == "5"
    assert message.apns.headers["apns-push-type"] == "background"
