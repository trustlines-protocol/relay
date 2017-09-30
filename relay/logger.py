import logging


def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    ch = logging.StreamHandler()
    ch.setLevel(level)
    formatter = logging.Formatter('%(asctime)s[%(levelname)s] %(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
