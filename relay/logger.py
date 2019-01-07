import logging


def get_logger(name, level=logging.INFO):
    # calling basicConfig multiple times does not have any effect, only the
    # first call initializes the logging system
    logging.basicConfig(format='%(asctime)s[%(levelname)s] %(name)s: %(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
