import codecs


def force_bytes(value, encoding='iso-8859-1'):
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    elif isinstance(value, str):
        return codecs.encode(value, encoding)
    else:
        raise TypeError("Unsupported type: {0}".format(type(value)))
