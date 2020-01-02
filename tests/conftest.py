import json
import operator
from collections import namedtuple
from pathlib import Path
from typing import Sequence

import hexbytes
import py
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(session, config, items):
    """mark tests in unit directory as unit tests and run them first

    this is not compatibe with the pytest-ordering plugin at the moment
    """
    unit_directory = py.path.local(__file__).dirpath().join("unit")

    def inside_unit_directory(item):
        return unit_directory.common(item.fspath) == unit_directory

    for item in items:
        if item.get_closest_marker("unit"):
            item._trustlines_sort_order = 0
        elif item.get_closest_marker("integration"):
            item._trustlines_sort_order = 1
        elif inside_unit_directory(item):
            item.add_marker(pytest.mark.unit)
            item._trustlines_sort_order = 0
        else:
            item.add_marker(pytest.mark.integration)
            item._trustlines_sort_order = 1
    items.sort(key=operator.attrgetter("_trustlines_sort_order"))


Account = namedtuple("Account", "address private_key")


@pytest.fixture(scope="session")
def addresses() -> Sequence[str]:
    return [
        "0x379162D7682cb8Bb6435c47E0B8B562eAFE66971",
        "0xA22d6A65531E1ecCc8f6a8580227036a2E4c7295",
        "0x57Dd8AC67427E8B270B9C15dEDd8B2501a8F7Fee",
        "0xea571341F70B2fE15716e494d1fF95A47d1cDc0E",
    ]


@pytest.fixture(scope="session")
def test_account():
    return Account(
        private_key=b"\x04HR\xb2\xa6p\xad\xe5@~x\xfb(c\xc5\x1d\xe9\xfc\xb9eB\xa0q\x86\xfe:\xed\xa6\xbb\x8a\x11m",
        address="0x82A978B3f5962A5b0957d9ee9eEf472EE55B42F1",
    )


@pytest.fixture(scope="session")
def test_extra_data():
    return hexbytes.HexBytes("0x12345678123456781234567812345678")


class TestDataReader:
    def __init__(self):
        self.testdata = {}
        testdata_directory = Path(__file__).absolute().parent / "testdata"
        for path in testdata_directory.glob("*.json"):
            self.testdata[path.name[:-5]] = json.load(open(path))["data"]

    def make_param(self, fixturename, count, data):
        return pytest.param(data, marks=[pytest.mark.testdata])

    def make_param_Transfer(self, fixturename, count, data):
        divisor = data["input_data"]["capacity_imbalance_fee_divisor"]
        fees_paid_by = data["input_data"]["fees_paid_by"]
        return pytest.param(
            data,
            marks=pytest.mark.testdata,
            id=f"Transfer-{count}-divisor-{divisor}-{fees_paid_by}-pays",
        )

    def pytest_generate_tests(self, metafunc):
        """read json files from testdata directory and generate tests from the testdata
        """
        for fixturename in metafunc.fixturenames:
            if fixturename in self.testdata:
                param = getattr(self, f"make_param_{fixturename}", self.make_param)
                metafunc.parametrize(
                    fixturename,
                    [
                        param(fixturename, count, data)
                        for count, data in enumerate(self.testdata[fixturename])
                    ],
                )


pytest_generate_tests = TestDataReader().pytest_generate_tests
