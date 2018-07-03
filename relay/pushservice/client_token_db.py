from typing import Iterable


class ClientTokenDB:

    def get_client_tokens(self, user_address: str) -> Iterable[str]:
        raise NotImplementedError

    def add_client_token(self, user_address: str, client_token: str):
        pass

    def delete_client_token(self, user_address: str, client_token: str):
        pass
