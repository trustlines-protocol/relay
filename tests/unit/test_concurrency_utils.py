import gevent

from relay.concurrency_utils import synchronized


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
