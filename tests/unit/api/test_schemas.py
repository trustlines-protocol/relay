#! pytest


import attr
import pytest
from hexbytes import HexBytes
from marshmallow import ValidationError
from tldeploy import identity
from web3.datastructures import AttributeDict

from relay.api import schemas
from relay.blockchain.currency_network_events import TransferEvent
from relay.network_graph.payment_path import FeePayer, PaymentPath

a_valid_meta_transaction = identity.MetaTransaction(
    from_="0xF2E246BB76DF876Cef8b38ae84130F4F55De395b",
    to="0x51a240271AB8AB9f9a21C82d9a85396b704E164d",
    chain_id=0,
    value=0,
    data=bytes.fromhex(
        "46432830000000000000000000000000000000000000000000000000000000000000000a"
    ),
    nonce=1,
    signature=bytes.fromhex(
        "6d2fe56ef6648cb3f0398966ad3b05d891cde786d8074bdac15bcb92ebfa722248"
        "9b8eb6ed87165feeede19b031bb69e12036a5fa13b3a46ad0c2c19d051ea9101"
    ),
)


web3_transfer_event = AttributeDict(
    {
        "args": AttributeDict(
            {
                "_from": "0xF2E246BB76DF876Cef8b38ae84130F4F55De395b",
                "_to": "0x51a240271AB8AB9f9a21C82d9a85396b704E164d",
                "_value": 10,
                "_extraData": HexBytes("0x"),
            }
        ),
        "event": "Transfer",
        "logIndex": 0,
        "transactionIndex": 0,
        "transactionHash": HexBytes(
            "0xfb95ccb6ab39e19821fb339dee33e7afe2545527725b61c64490a5613f8d11fa"
        ),
        "address": "0xF2E246BB76DF876Cef8b38ae84130F4F55De395b",
        "blockHash": HexBytes(
            "0xd74c3e8bdb19337987b987aee0fa48ed43f8f2318edfc84e3a8643e009592a68"
        ),
        "blockNumber": 3,
    }
)


def gen_meta_transactions():
    mt = a_valid_meta_transaction
    return [
        mt,
        attr.evolve(mt, data=b""),
        attr.evolve(mt, nonce=0),
        attr.evolve(mt, value=1234),
        attr.evolve(mt, nonce=2 ** 256 - 1),
        attr.evolve(mt, data=HexBytes("0xab")),
    ]


@pytest.mark.parametrize("meta_transaction", gen_meta_transactions())
def test_meta_transaction_roundtrip(meta_transaction):
    dumped = schemas.MetaTransactionSchema().dump(meta_transaction)
    print("DUMPED", dumped)

    loaded = schemas.MetaTransactionSchema().load(dumped)
    print("LOADED", loaded)

    assert loaded == meta_transaction


@pytest.mark.parametrize(
    "values",
    [
        dict(nonce="-1"),
        dict(nonce=1),
        dict(nonce=str(2 ** 256)),
        dict(data=""),
        dict(data="0xa"),
        dict(data="0xgg"),
        dict(data="x00"),
        dict(value="-1"),
        dict(value=str(2 ** 256)),
        dict(value="1.5"),
        dict(signature=""),
        dict(signature="0x" + "00" * 64),
        dict(signature="0x" + "00" * 66),
    ],
)
def test_load_meta_transaction_invalid_values(values):
    dumped = schemas.MetaTransactionSchema().dump(a_valid_meta_transaction)
    dumped.update(values)
    with pytest.raises(ValidationError):
        schemas.MetaTransactionSchema().load(dumped)


@pytest.mark.parametrize(
    "values",
    [
        dict(nonce="1"),
        dict(data="0x00"),
        dict(data="0xff"),
        dict(feeRecipient="0x" + "1" * 40),
        dict(nonce=str(2 ** 256 - 1)),
        dict(value="1"),
        dict(value=str(2 ** 256 - 1)),
        dict(value="15"),
        dict(signature="0x" + "00" * 65),
    ],
)
def test_load_meta_transaction_valid_values(values):
    dumped = schemas.MetaTransactionSchema().dump(a_valid_meta_transaction)
    dumped.update(values)
    # If the load fails, a `<marshmallow.exceptions.ValidationError>` is raised
    schemas.MetaTransactionSchema().load(dumped)


@pytest.fixture(params=[FeePayer.SENDER, FeePayer.RECEIVER])
def payment_path(request):

    cost = 1
    path = []
    value = 1
    fee_payer = request.param

    return PaymentPath(cost, path, value, fee_payer=fee_payer)


def test_payment_path_roundtrip(payment_path):

    dumped = schemas.PaymentPathSchema().dump(payment_path)
    print("DUMPED", dumped)

    loaded = schemas.PaymentPathSchema().load(dumped)
    print("LOADED", loaded)

    assert loaded == payment_path


def test_no_class_type_in_event():
    event = TransferEvent(web3_transfer_event, 10, 1000)

    dumped = schemas.AnyEventSchema().dump(event)

    assert dumped.get(schemas.AnyEventSchema.type_field) is None
    assert dumped["amount"] == str(event.value)
    assert dumped["from"] == event.from_
    assert dumped["extraData"] == event.extra_data.hex()
