from functools import wraps

from tinyrpc.protocols.jsonrpc import JSONRPCInvalidParamsError
from marshmallow import ValidationError


def validating_rpc_caller(method, args, kwargs, client):
    if len(args) > 0:
        raise JSONRPCInvalidParamsError('No positional arguments allowed')
    try:
        return method(client, **kwargs)
    except ValidationError as e:
        raise JSONRPCInvalidParamsError('Invalid params:'+str(e.messages))
    except Exception as e:
        raise Exception('Internal server error: ' + str(e))


def check_args(schema):
    def check_args_decorator(func):
        @wraps(func)
        def func_wrapper(*args, **kwargs):
            data = schema.load(kwargs).data
            return func(*args, **data)
        return func_wrapper
    return check_args_decorator
