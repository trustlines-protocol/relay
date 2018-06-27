from typing import Iterable


class ClientTokenDB:

    def get_client_tokens(self, user_address: str) -> Iterable[str]:
        raise NotImplementedError
