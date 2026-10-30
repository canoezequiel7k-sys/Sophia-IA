from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: str


class HttpStatusError(Exception):
    def __init__(self, status: int, body_text: str, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body_text = body_text
        self.headers = dict(headers or {})


class ConnectionFailed(Exception):
    pass


def post_json(url: str, headers: Mapping[str, str], payload: dict[str, Any], timeout: float) -> HttpResponse:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return HttpResponse(response.status, dict(response.headers.items()), raw)
    except urllib.error.HTTPError as err:
        text = err.read().decode("utf-8", errors="replace")
        raise HttpStatusError(err.code, text, dict(err.headers.items()) if err.headers else {}) from None
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise ConnectionFailed(str(err)) from None
