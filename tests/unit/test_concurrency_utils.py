import pytest
import gevent

from relay.concurrency_utils import joinall, TimeoutException, synchronized


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


def unsafe_list_operation(lst):
    """this function provides an unsafe list operation

    It appends the length of the list to the list itself, but does so in a way
    that allows race conditions to happen when called from multiple greenlets
    at the same time because it sleeps a bit inbetween taking the length of the
    list and appending the length.

    It's used for testing the synchronized operator.
    """
    count = len(lst)
    gevent.sleep(0.01)
    lst.append(count)


def test_synchronized_function():
    """test that the @synchronized operator works on functions"""
    lst = []

    @synchronized
    def doit():
        unsafe_list_operation(lst)

    greenlets = [gevent.spawn(doit) for i in range(4)]
    gevent.joinall(greenlets, raise_error=True)

    assert lst == list(range(4))


def test_synchronized_method():
    """test that the @synchronized operator works on methods"""
    lst = []

    class Foo:
        @synchronized
        def doit(self):
            unsafe_list_operation(lst)

    foo = Foo()
    greenlets = [gevent.spawn(foo.doit) for i in range(4)]
    gevent.joinall(greenlets, raise_error=True)

    assert lst == list(range(4))
