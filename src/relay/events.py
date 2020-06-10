from relay.network_graph.graph import AggregatedAccountSummary


class Event(object):

    type = "Event"

    def __init__(self, timestamp: int) -> None:
        self.timestamp = timestamp

    def __str__(self):
        return f"<Event: type={self.type}, timestamp={self.timestamp}>"


class AccountEvent(Event):
    def __init__(
        self,
        network_address: str,
        user: str,
        account_summary: AggregatedAccountSummary,
        timestamp: int,
    ) -> None:
        super().__init__(timestamp)
        self.user = user
        self.balance = account_summary.balance
        self.creditline_given = account_summary.creditline_given
        self.creditline_received = account_summary.creditline_received
        self.left_given = account_summary.creditline_left_given
        self.left_received = account_summary.creditline_left_received
        self.network_address = network_address


class BalanceEvent(AccountEvent):

    type = "BalanceUpdate"

    def __init__(
        self,
        network_address: str,
        from_: str,
        to: str,
        account_summary: AggregatedAccountSummary,
        timestamp: int,
    ) -> None:
        super().__init__(network_address, from_, account_summary, timestamp)
        self.from_ = from_
        self.to = to
        self.counter_party = to


class NetworkBalanceEvent(AccountEvent):

    type = "NetworkBalance"


class MessageEvent(Event):

    type = "Message"

    def __init__(self, message: str, *, timestamp: int, type: str = None) -> None:
        super().__init__(timestamp)
        if type is not None:
            self.type = type
        self.message = message
