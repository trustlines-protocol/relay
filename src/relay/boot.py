# boot the main program, let gevent do it's monkeypatching and setup
# a greenlet aware custom logger class

# Make external libs work with gevent, but still enable real threading
from gevent import monkey  # isort:skip

monkey.patch_all(thread=False)  # noqa: E702 isort:skip
# Make postgresql usable with gevent
import psycogreen.gevent  # isort:skip

psycogreen.gevent.patch_psycopg()  # noqa: E702 isort:skip


import logging
import os
import sys

import gevent

LOGFORMAT = "%(asctime)-15s %(levelname)-9s[%(greenlet)s] %(name)s: %(message)s"


class CurrentGreenletLogger(logging.Logger):
    def _log(self, level, msg, args, exc_info=None, extra=None):
        if extra is None:
            extra = {"greenlet": getattr(gevent.getcurrent(), "name", "main")}
        super()._log(level, msg, args, exc_info, extra)


def setup_basic_logging():
    logging.setLoggerClass(CurrentGreenletLogger)
    logging.basicConfig(
        level=os.environ.get("LOGLEVEL", "INFO").upper(),
        format=LOGFORMAT,
        stream=sys.stdout,
    )


def main():
    setup_basic_logging()
    import relay.main

    relay.main.main()


if __name__ == "__main__":
    main()
