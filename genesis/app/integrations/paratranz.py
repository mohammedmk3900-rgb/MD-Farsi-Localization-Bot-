from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from app.integrations.contracts import ProjectStats


class ParaTranzError(RuntimeError):
    """Safe error for upstream transport, HTTP, and response-shape failures."""


@dataclass(frozen=True)
class ParaTranzConfig:
    project_id: int
    base_url: str = "https://paratranz.cn/api"
    timeout: float = 15.0
    max_retries: int = 3
    page_size: int = 100
    max_pages: int = 100

    @classmethod
    def from_env(cls) -> "ParaTranzConfig":
        raw = os.getenv("PARATRANZ_PROJECT_ID", "19621")
        return cls(
            project_id=int(raw),
            base_url=os.getenv("PARATRANZ_BASE_URL", "https://paratranz.cn/api").rstrip("/"),
            timeout=max(1.0, float(os.getenv("PARATRANZ_TIMEOUT_SECONDS", "15"))),
            max_retries=max(0, min(5, int(os.getenv("PARATRANZ_MAX_RETRIES", "3")))),
            page_size=max(1, min(1000, int(os.getenv("PARATRANZ_PAGE_SIZE", "100")))),
            max_pages=max(1, min(500, int(os.getenv("PARATRANZ_MAX_PAGES", "100")))),
        )


class ParaTranzIntegration:
    """Read-only, resilient adapter for ParaTranz project, file and glossary APIs.

    ParaTranz's documented authentication format is the raw API token in the
    Authorization header, not a Bearer-prefixed token.
    """

    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    def __init__(self, config: ParaTranzConfig | None = None, token: str | None = None, timeout: float | None = None):
        self.config = config or ParaTranzConfig.from_env()
        raw_token = token if token is not None else os.getenv("PARATRANZ_TOKEN", "")
        self.token = (raw_token or "").strip()
        if self.token.lower().startswith("bearer "):
            self.token = self.token[7:].strip()
        self.timeout = max(1.0, float(timeout if timeout is not None else self.config.timeout))

    def _get(self, path: str) -> object:
        if not path or path.startswith(("http://", "https://", "//")):
            raise ValueError("ParaTranz path must be relative")
        url = urljoin(self.config.base_url.rstrip("/") + "/", path.lstrip("/"))
        headers = {"Accept": "application/json", "User-Agent": "MD-News-Genesis/11"}
        if self.token:
            headers["Authorization"] = self.token
        request_url = url
        request = None

        for attempt in range(self.config.max_retries + 1):
            request = Request(request_url, method="GET", headers=headers)
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8")
                    try:
                        return json.loads(raw)
                    except (ValueError, json.JSONDecodeError) as exc:
                        raise ParaTranzError("ParaTranz returned invalid JSON") from exc
            except HTTPError as exc:
                status = exc.code
                if status in self.RETRYABLE_STATUS and attempt < self.config.max_retries:
                    delay = self._retry_delay(exc.headers.get("Retry-After") if exc.headers else None, attempt)
                    exc.close()
                    time.sleep(delay)
                    continue
                message, api_code = self._error_details(exc)
                suffix = f" (API code {api_code})" if api_code is not None else ""
                raise ParaTranzError(f"ParaTranz HTTP {status}: {message}{suffix}") from None
            except (URLError, TimeoutError) as exc:
                if attempt < self.config.max_retries:
                    time.sleep(min(8.0, 0.5 * (2 ** attempt)))
                    continue
                reason = type(exc).__name__
                raise ParaTranzError(f"ParaTranz transport failure ({reason})") from None

        raise ParaTranzError("ParaTranz request exhausted retries")

    @staticmethod
    def _retry_delay(value: str | None, attempt: int) -> float:
        if value:
            try:
                return min(30.0, max(0.0, float(value)))
            except ValueError:
                try:
                    from datetime import datetime, timezone
                    parsed = parsedate_to_datetime(value)
                    return min(30.0, max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds()))
                except (TypeError, ValueError, OverflowError):
                    pass
        return min(8.0, 0.5 * (2 ** attempt))

    @staticmethod
    def _error_details(exc: HTTPError) -> tuple[str, int | str | None]:
        message = "request failed"
        api_code = None
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError, OSError):
            body = None
        if isinstance(body, dict):
            raw_message = body.get("message") or body.get("error")
            if isinstance(raw_message, str) and raw_message.strip():
                message = raw_message.strip()[:250]
            raw_code = body.get("code")
            if isinstance(raw_code, (int, str)) and not isinstance(raw_code, bool):
                api_code = raw_code
        return message, api_code

    @staticmethod
    def _payload(data: object) -> object:
        if isinstance(data, dict) and isinstance(data.get("data"), (dict, list)):
            return data["data"]
        return data

    @classmethod
    def _list_payload(cls, data: object, keys: tuple[str, ...]) -> tuple[list[dict], dict]:
        data = cls._payload(data)
        if isinstance(data, list):
            if not all(isinstance(item, dict) for item in data):
                raise ParaTranzError("ParaTranz list response contains invalid entries")
            return data, {}
        if isinstance(data, dict):
            for key in (*keys, "results", "items", "rows"):
                value = data.get(key)
                if isinstance(value, list):
                    if not all(isinstance(item, dict) for item in value):
                        raise ParaTranzError(f"ParaTranz collection {key!r} contains invalid entries")
                    return value, data
        raise ParaTranzError("ParaTranz list response has an unrecognized shape")

    @staticmethod
    def _metric(value: object, field: str) -> int:
        if isinstance(value, bool) or value is None:
            raise ParaTranzError(f"ParaTranz metric {field!r} is invalid")
        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ParaTranzError(f"ParaTranz metric {field!r} is invalid") from exc
        if isinstance(value, float) and not value.is_integer():
            raise ParaTranzError(f"ParaTranz metric {field!r} is invalid")
        if isinstance(value, str) and str(result) != value.strip():
            raise ParaTranzError(f"ParaTranz metric {field!r} is invalid")
        if result < 0:
            raise ParaTranzError(f"ParaTranz metric {field!r} cannot be negative")
        return result

    def project(self) -> dict:
        payload = self._payload(self._get(f"projects/{self.config.project_id}"))
        if not isinstance(payload, dict):
            raise ParaTranzError("ParaTranz project response is not an object")
        returned_id = payload.get("id")
        if returned_id is not None and self._metric(returned_id, "project.id") != self.config.project_id:
            raise ParaTranzError("ParaTranz returned a different project than requested")
        return payload

    def files(self) -> list[dict]:
        payload = self._get(f"projects/{self.config.project_id}/files")
        files, _ = self._list_payload(payload, ("files",))
        return files

    def _list_all(self, path: str, keys: tuple[str, ...]) -> list[dict]:
        items: list[dict] = []
        seen: set[str] = set()
        previous_signature: str | None = None
        for page in range(1, self.config.max_pages + 1):
            query = urlencode({"page": page, "pageSize": self.config.page_size})
            payload = self._get(f"{path}?{query}")
            batch, metadata = self._list_payload(payload, keys)
            if not batch:
                break
            signature = json.dumps(batch, sort_keys=True, ensure_ascii=False, default=str)
            if signature == previous_signature:
                break
            previous_signature = signature
            for item in batch:
                identity = item.get("id")
                key = f"id:{identity}" if identity is not None else json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)
                if key not in seen:
                    seen.add(key)
                    items.append(item)
            total_pages = next((metadata.get(k) for k in ("pageCount", "page_count", "totalPages", "total_pages", "pages") if isinstance(metadata.get(k), int)), None)
            total_rows = next((metadata.get(k) for k in ("rowCount", "total", "totalCount", "total_count", "count") if isinstance(metadata.get(k), int)), None)
            if total_pages is not None:
                if page >= total_pages:
                    break
                continue
            if total_rows is not None:
                if len(items) >= total_rows:
                    break
                continue
            if len(batch) < self.config.page_size:
                break
        else:
            raise ParaTranzError("ParaTranz pagination exceeded safety limit")
        return items

    def members(self) -> list[dict]:
        return self._list_all(f"projects/{self.config.project_id}/members", ("members",))

    def stats(self) -> ProjectStats:
        project = self.project()
        files = self.files()
        if not files:
            raise ParaTranzError("ParaTranz returned no project files; refusing to publish an empty snapshot")

        totals = {"total": 0, "translated": 0, "reviewed": 0, "words": 0}
        for index, file in enumerate(files):
            name = file.get("name", str(index))
            for key in totals:
                if key not in file or file[key] is None:
                    raise ParaTranzError(f"ParaTranz file {name!r} is missing metric {key!r}")
                totals[key] += self._metric(file[key], f"file.{key}")
        if totals["total"] <= 0:
            raise ParaTranzError("ParaTranz project contains no strings; refusing to publish an empty snapshot")
        if totals["translated"] > totals["total"] or totals["reviewed"] > totals["total"]:
            raise ParaTranzError("ParaTranz project counters exceed total strings")

        raw_members = project.get("members", project.get("memberCount"))
        if isinstance(raw_members, list):
            member_count = len(raw_members)
        elif raw_members is not None:
            member_count = self._metric(raw_members, "members")
        else:
            member_count = len(self.members())

        return ProjectStats(
            project_id=self.config.project_id,
            words_total=totals["words"],
            strings_total=totals["total"],
            translated=totals["translated"],
            reviewed=totals["reviewed"],
            files=len(files),
            members=member_count,
        )

    def glossary(self) -> list[dict]:
        return self._list_all(f"projects/{self.config.project_id}/terms", ("terms", "glossary"))
