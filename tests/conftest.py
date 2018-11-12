import os
import sys
from typing import Sequence
from collections import namedtuple

import pytest
import py
import operator

# import the relay module so no pip install is necessary
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


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


Account = namedtuple('Account', 'address private_key')


@pytest.fixture(scope="session")
def addresses() -> Sequence[str]:
    return [
        '0x379162D7682cb8Bb6435c47E0B8B562eAFE66971',
        '0xA22d6A65531E1ecCc8f6a8580227036a2E4c7295',
        '0x57Dd8AC67427E8B270B9C15dEDd8B2501a8F7Fee',
        '0xea571341F70B2fE15716e494d1fF95A47d1cDc0E'
    ]


@pytest.fixture(scope="session")
def test_account():
    return Account(
        private_key=b'\x04HR\xb2\xa6p\xad\xe5@~x\xfb(c\xc5\x1d\xe9\xfc\xb9eB\xa0q\x86\xfe:\xed\xa6\xbb\x8a\x11m',
        address='0x82A978B3f5962A5b0957d9ee9eEf472EE55B42F1')
