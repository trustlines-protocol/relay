from .proxy import Proxy
from relay.exchange.order import Order

FillEvent = 'LogFill'
CancelEvent = 'LogCancel'


class ExchangeProxy(Proxy):
    def __init__(
            self,
            web3,
            exchange_abi,
            token_abi,
            address: str,
            address_oracle
    ) -> None:
        super().__init__(web3, exchange_abi, address)
        self._token_abi = token_abi
        self._address_oracle = address_oracle

    def validate(self, order: Order) -> bool:
        return (order.exchange_address == self.address and
                self.validate_funds(order) and
                self.validate_filled_amount(order))

    def validate_funds(self, order: Order) -> bool:
        if self._is_currency_network(order.maker_token):
            return True
        else:
            maker_token = self._token_contract(address=order.maker_token)
            return (maker_token.call().balanceOf(order.maker_address) >= order.maker_token_amount and
                    (self._is_trusted_token(order.maker_token) or
                     maker_token.call().allowance(order.maker_address, self.address) >= order.maker_token_amount))

    def validate_filled_amount(self, order: Order) -> bool:
        return self._proxy.call().getUnavailableTakerTokenAmount(order.hash()) < order.taker_token_amount

    def get_filled_amount(self, order: Order) -> int:
        return self._proxy.call().filled(order.hash())

    def get_cancelled_amount(self, order: Order) -> int:
        return self._proxy.call().cancelled(order.hash())

    def get_unavailable_amount(self, order: Order) -> int:
        return self._proxy.call().getUnavailableTakerTokenAmount(order.hash())

    def start_listen_on_fill(self, f) -> None:
        def log(log_entry):
            f(log_entry['args']['orderHash'],
              log_entry['args']['filledMakerTokenAmount'],
              log_entry['args']['filledTakerTokenAmount'])
        self.start_listen_on(FillEvent, log)

    def start_listen_on_cancel(self, f) -> None:
        def log(log_entry):
            f(log_entry['args']['orderHash'],
              log_entry['args']['cancelledMakerTokenAmount'],
              log_entry['args']['cancelledTakerTokenAmount'])
        self.start_listen_on(CancelEvent, log)

    def _is_currency_network(self, token_address: str) -> bool:
        return self._address_oracle.is_currency_network(token_address)

    def _is_trusted_token(self, token_address: str) -> bool:
        return self._address_oracle.is_trusted_token(token_address)

    def _token_contract(self, address: str):
        return self._web3.eth.contract(abi=self._token_abi, address=address)


class DummyExchangeProxy():

    def __init__(self, exchange_address: str) -> None:
        self.address = exchange_address

    def validate(self, order: Order) -> bool:
        return True

    def validate_funds(self, order: Order) -> bool:
        return True

    def validate_filled_amount(self, order: Order) -> bool:
        return True

    def get_filled_amount(self, order: Order) -> int:
        return 0

    def start_listen_on_fill(self, f) -> None:
        pass

    def start_listen_on_cancel(self, f) -> None:
        pass
