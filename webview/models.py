from copy import copy
from typing import Optional


class Request:
    def __init__(self, url: str, method: str, headers: dict, content_stream: bytearray) -> None:
        self.url = url
        self.method = method
        self.headers = copy(headers)
        self.content_stream = content_stream
        self.response: Optional[Response] = None

    def __repr__(self) -> str:
        return f'Request to {self.url} - {self.method}'


class Response:
    def __init__(self, url: str, status_code: int = 200, headers=None, content_stream: bytearray = bytearray(), reason_phrase: str = 'OK') -> None:
        if headers is None:
            headers = {}
        self.url = url
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        self.headers = headers
        self.content_stream: bytearray = content_stream

    def __repr__(self) -> str:
        return f'Response from {self.url} - {self.status_code}'
