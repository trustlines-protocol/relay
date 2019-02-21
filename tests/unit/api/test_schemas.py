#! pytest


import pytest
import attr
from hexbytes import HexBytes
from tldeploy import identity
from relay.api import schemas
from marshmallow import ValidationError
from relay.network_graph.payment_path import PaymentPath, FeePayer


a_valid_meta_transaction = identity.MetaTransaction(
    from_="0xF2E246BB76DF876Cef8b38ae84130F4F55De395b",
    to="0x51a240271AB8AB9f9a21C82d9a85396b704E164d",
    value=0,
    data=bytes.fromhex(
        "46432830000000000000000000000000000000000000000000000000000000000000000a"
    ),
    nonce=1,
    extra_data=b"",
    signature=bytes.fromhex(
        "6d2fe56ef6648cb3f0398966ad3b05d891cde786d8074bdac15bcb92ebfa722248"
        "9b8eb6ed87165feeede19b031bb69e12036a5fa13b3a46ad0c2c19d051ea9101"
    ),
)


def gen_meta_transactions():
    mt = a_valid_meta_transaction
    return [
        mt,
        attr.evolve(mt, data=b""),
        attr.evolve(mt, extra_data=b"foo"),
        attr.evolve(mt, nonce=0),
        attr.evolve(mt, value=1234),
        attr.evolve(mt, nonce=2 ** 256 - 1),
        attr.evolve(mt, data=HexBytes("0xab")),
    ]


@pytest.mark.parametrize("meta_transaction", gen_meta_transactions())
def test_meta_transaction_roundtrip(meta_transaction):
    dumped = schemas.MetaTransactionSchema().dump(meta_transaction).data
    print("DUMPED", dumped)

    loaded = schemas.MetaTransactionSchema().load(dumped).data
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
    dumped = schemas.MetaTransactionSchema().dump(a_valid_meta_transaction).data
    dumped.update(values)
    with pytest.raises(ValidationError):
        schemas.MetaTransactionSchema().load(dumped)


@pytest.mark.parametrize(
    "values",
    [
        dict(nonce="1"),
        dict(data="0x00"),
        dict(data="0xff"),
        dict(extraData="0x00"),
        dict(nonce=str(2 ** 256 - 1)),
        dict(value="1"),
        dict(value=str(2 ** 256 - 1)),
        dict(value="15"),
        dict(signature="0x" + "00" * 65),
    ],
)
def test_load_meta_transaction_valid_values(values):
    dumped = schemas.MetaTransactionSchema().dump(a_valid_meta_transaction).data
    dumped.update(values)
    assert not schemas.MetaTransactionSchema().load(dumped).errors


@pytest.fixture(params=[FeePayer.SENDER, FeePayer.RECEIVER])
def payment_path(request):

    cost = 1
    path = []
    value = 1
    fee_payer = request.param
    estimated_gas = 0

    return PaymentPath(
        cost, path, value, fee_payer=fee_payer, estimated_gas=estimated_gas
    )


def test_payment_path_roundtrip(payment_path):

    dumped = schemas.PaymentPathSchema().dump(payment_path).data
    print("DUMPED", dumped)

    loaded = schemas.PaymentPathSchema().load(dumped).data
    print("LOADED", loaded)

    assert loaded == payment_path
