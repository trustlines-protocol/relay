"""this test file is mostly here to test that we can import the main module

importing may not work when we forgot to declare some dependencies.
"""

import re
from relay import main


def test_get_version():
    version = main.get_version()
    print(f"VERSION {version!r}")
    assert re.match(r"^\d+", version), "version should start with a number"
