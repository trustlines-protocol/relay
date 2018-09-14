from typing import Callable, List, Any, Iterable
import wrapt

import gevent
import gevent.lock


class TimeoutException(Exception):
    """Exception to signal that the job could not be finished in time"""
    pass


def joinall(functions: Iterable[Callable], timeout: float = None) -> List[Any]:
    """
    Executes functions by spawning gevent greenlets and waiting for them
    to finish up to `timeout` seconds.
    If timing out, a TimeoutException is thrown
    Args:
        functions: The functions to execute each in a greenlet
        timeout: Seconds to wait until timing out

    Returns: The results of the executed functions

    """
    spawned_greenlets = [gevent.spawn(fun) for fun in functions]
    finished_greenlets = gevent.joinall(greenlets=spawned_greenlets, timeout=timeout, raise_error=True)
    if len(finished_greenlets) < len(spawned_greenlets):
        raise TimeoutException('Could not finish all jobs before the timeout')

    return [g.value for g in spawned_greenlets if g.value is not None]  # Use spawned greenlets to preserve order


# adapted from https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/07-the-missing-synchronized-decorator.md
@wrapt.decorator
def synchronized(wrapped, instance, args, kwargs):
    if instance is None:
        owner = wrapped
    else:
        owner = instance

    lock = vars(owner).get('_synchronized_lock', None)

    # we don't need to lock here since it's gevent, not real threading
    if lock is None:
        lock = gevent.lock.RLock()
        setattr(owner, '_synchronized_lock', lock)

    with lock:
        return wrapped(*args, **kwargs)
