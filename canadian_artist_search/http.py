from __future__ import annotations

import json
import time
from dataclasses import dataclass
from http.client import HTTPResponse
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class JsonHttpClient:
    user_agent: str
    timeout: float = 30.0
    retries: int = 3

    def get_json(self, url: str, params: dict[str, object]) -> dict[str, Any]:
        query = urlencode({key: value for key, value in params.items() if value is not None})
        full_url = f"{url}?{query}" if query else url

        for attempt in range(self.retries + 1):
            request = Request(full_url, headers={"User-Agent": self.user_agent})
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    return _load_json_response(response)
            except HTTPError as error:
                if not _should_retry(error.code) or attempt == self.retries:
                    raise
                time.sleep(_retry_delay(error, attempt))
            except URLError:
                if attempt == self.retries:
                    raise
                time.sleep(2**attempt)

        raise RuntimeError("exhausted HTTP retry loop")


def _load_json_response(response: HTTPResponse) -> dict[str, Any]:
    payload = response.read().decode("utf-8")
    loaded = json.loads(payload)
    if not isinstance(loaded, dict):
        raise ValueError("expected a JSON object response")
    return loaded


def _should_retry(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


def _retry_delay(error: HTTPError, attempt: int) -> float:
    retry_after = error.headers.get("Retry-After")
    if retry_after:
        try:
            return max(1.0, float(retry_after))
        except ValueError:
            pass
    return float(2**attempt)
