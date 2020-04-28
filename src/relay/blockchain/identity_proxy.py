from .identity_events import event_builders
from .proxy import Proxy


class IdentityProxy(Proxy):

    event_builders = event_builders
