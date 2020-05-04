import gevent
import gevent.lock
import wrapt


# adapted from https://github.com/GrahamDumpleton/wrapt/blob/develop/blog/07-the-missing-synchronized-decorator.md
@wrapt.decorator
def synchronized(wrapped, instance, args, kwargs):
    if instance is None:
        owner = wrapped
    else:
        owner = instance

    lock = vars(owner).get("_synchronized_lock", None)

    # we don't need to lock here since it's gevent, not real threading
    if lock is None:
        lock = gevent.lock.RLock()
        setattr(owner, "_synchronized_lock", lock)

    with lock:
        return wrapped(*args, **kwargs)
