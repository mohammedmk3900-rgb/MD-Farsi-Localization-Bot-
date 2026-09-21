#!/usr/bin/env python3
"""Stdlib-only HTTP client with bounded retry and Discord 429 support."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

RETRYABLE = {429, 500, 502, 503, 504}

def request_json(url, method="GET", payload=None, headers=None, retries=3, timeout=30):
    base = {"Accept": "application/json", "User-Agent": "MD-Farsi-Localization-Command-Center/7.0"}
    if headers:
        base.update(headers)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    if body:
        base["Content-Type"] = "application/json"
    last = None
    for attempt in range(retries):
        try:
            with urlopen(Request(url, data=body, headers=base, method=method), timeout=timeout) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:800]
            retry_after = exc.headers.get("Retry-After")
            last = RuntimeError(f"HTTP {exc.code}: {detail}")
            if exc.code not in RETRYABLE or attempt >= retries - 1:
                raise last
            delay = float(retry_after) if retry_after else 2**attempt
            time.sleep(min(delay, 30))
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = RuntimeError(str(exc))
            if attempt >= retries - 1:
                raise last
            time.sleep(min(2**attempt, 10))
    raise last or RuntimeError("HTTP request failed")
