import os
import sys
from typing import Sequence

import pytest

# import the relay module so no pip install is necessary
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture(scope="session", autouse=True)
def silence_deprecation_warnings():
    from relay.main import patch_warnings_module
    patch_warnings_module()


@pytest.fixture()
def addresses() -> Sequence[str]:
    return [
        '0x379162D7682cb8Bb6435c47E0B8B562eAFE66971',
        '0xA22d6A65531E1ecCc8f6a8580227036a2E4c7295',
        '0x57Dd8AC67427E8B270B9C15dEDd8B2501a8F7Fee',
        '0xea571341F70B2fE15716e494d1fF95A47d1cDc0E'
    ]
