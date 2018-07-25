import pytest
import gevent

from relay.concurrency_utils import joinall, TimeoutException


def test_success():
    def f():
        return 3

    def g():
        return 4

    def h():
        return 5

    result = joinall([f, g, h], timeout=1.)

    assert result == [3, 4, 5]


def test_timeout():
    def f():
        return 3

    def g():
        gevent.sleep(5.)
        return 4

    def h():
        return 5

    with pytest.raises(TimeoutException):
        joinall([f, g, h], timeout=1.)


def test_timeout_not_enough():
    def f():
        return 3

    def g():
        gevent.sleep(5.)
        return 4

    def h():
        gevent.sleep(5.)
        return 5

    with pytest.raises(TimeoutException):
        joinall([f, g, h], timeout=1.)


def test_no_timeout():
    def f():
        return 3

    def g():
        gevent.sleep(0.5)
        return 4

    def h():
        return 5

    result = joinall([f, g, h])

    assert result == [3, 4, 5]
