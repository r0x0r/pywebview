from copy import copy
from typing import Any


class Request:
    def __init__(self, url: str, method: str, headers: dict[str, Any]) -> None:
        self.url = url
        self.method = method
        self.headers = copy(headers)

    def __repr__(self) -> str:
        return f'Request to {self.url} - {self.method}'


class Response:
    def __init__(self, url: str, status_code: int, headers: dict[str, Any]) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = copy(headers)

    def __repr__(self) -> str:
        return f'Response from {self.url} - {self.status_code}'
