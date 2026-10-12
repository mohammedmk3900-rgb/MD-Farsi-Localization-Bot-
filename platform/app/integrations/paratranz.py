from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import Settings
from app.domain.models import ProjectSnapshot


class ParaTranzAPIError(RuntimeError):
    """Safe, structured error raised for failed ParaTranz requests."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        api_code: int | str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.api_code = api_code
        self.retryable = retryable


class ParaTranzDataError(ValueError):
    """Raised when ParaTranz returns a successful but unusable payload."""


def _unwrap_data(payload: Any) -> Any:
    # Some API deployments wrap their payload in {"data": ...}; the
    # documented API also returns project objects and file arrays directly.
    if isinstance(payload, dict) and "data" in payload:
        data = payload["data"]
        if isinstance(data, (dict, list)):
            return data
    return payload


def _list_payload(payload: Any, collection_keys: tuple[str, ...]) -> tuple[list[dict], dict]:
    payload = _unwrap_data(payload)
    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise ParaTranzDataError("ParaTranz returned a list containing non-object entries")
        return payload, {}

    if not isinstance(payload, dict):
        raise ParaTranzDataError("ParaTranz returned an unexpected list response")

    # Common API/OpenAPI response shapes. Do not silently turn unknown
    # successful payloads into empty lists: that can erase a valid glossary.
    for key in (*collection_keys, "results", "items", "rows"):
        value = payload.get(key)
        if isinstance(value, list):
            if not all(isinstance(item, dict) for item in value):
                raise ParaTranzDataError(f"ParaTranz field {key!r} contains non-object entries")
            return value, payload
    raise ParaTranzDataError("ParaTranz list response did not contain a recognized collection")


def _as_nonnegative_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or value is None:
        raise ParaTranzDataError(f"ParaTranz metric {field!r} is not an integer")
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ParaTranzDataError(f"ParaTranz metric {field!r} is not an integer") from exc
    if isinstance(value, float) and not value.is_integer():
        raise ParaTranzDataError(f"ParaTranz metric {field!r} is not an integer")
    if isinstance(value, str) and str(result) != value.strip():
        raise ParaTranzDataError(f"ParaTranz metric {field!r} is not an integer")
    if result < 0:
        raise ParaTranzDataError(f"ParaTranz metric {field!r} cannot be negative")
    return result


class ParaTranzAPI:
    """Read-only, resilient HTTP layer for the ParaTranz REST API.

    ParaTranz documents the API token as the raw Authorization header value
    (not a Bearer token). Retries are restricted to safe GET requests and
    transient transport/server/rate-limit failures.
    """

    DEFAULT_BASE_URL = "https://paratranz.cn/api"
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        token: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 20.0,
        max_retries: int = 3,
    ) -> None:
        self.token = (token or "").strip()
        # Accept a pasted "Bearer <token>" value but normalize it to the
        # raw token format expected by ParaTranz's API documentation.
        if self.token.lower().startswith("bearer "):
            self.token = self.token[7:].strip()
        self.base_url = base_url.rstrip("/") + "/"
        self.timeout = max(1.0, float(timeout))
        self.max_retries = max(0, min(int(max_retries), 5))

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(30.0, max(0.0, float(retry_after)))
                except ValueError:
                    try:
                        date = parsedate_to_datetime(retry_after)
                        return min(30.0, max(0.0, (date - datetime.now(timezone.utc)).total_seconds()))
                    except (TypeError, ValueError, OverflowError):
                        pass
        return min(8.0, 0.5 * (2 ** attempt))

    @staticmethod
    def _error_payload(response: httpx.Response) -> tuple[str, int | str | None]:
        message = f"HTTP {response.status_code}"
        api_code = None
        try:
            body = response.json()
        except (ValueError, json.JSONDecodeError):
            body = None
        if isinstance(body, dict):
            raw_message = body.get("message") or body.get("error")
            if isinstance(raw_message, str) and raw_message.strip():
                # Bound untrusted server text and redact a token if an upstream
                # error ever echoes request credentials.
                message = raw_message.strip()[:300]
                if self_token := getattr(response, "_paratranz_token", None):
                    message = message.replace(self_token, "[redacted]")
            raw_code = body.get("code")
            if isinstance(raw_code, (str, int)) and not isinstance(raw_code, bool):
                api_code = raw_code
        return message, api_code

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        if not self.token:
            raise ParaTranzAPIError("PARATRANZ_TOKEN is not configured")
        if not path or path.startswith(("http://", "https://", "//")):
            raise ValueError("ParaTranz path must be a relative API path")

        url = urljoin(self.base_url + "/", path.lstrip("/"))
        headers = {
            "Authorization": self.token,
            "Accept": "application/json",
            "User-Agent": "MD-Farsi-Localization-Platform/1.1",
        }

        for attempt in range(self.max_retries + 1):
            response: httpx.Response | None = None
            try:
                with httpx.Client(
                    timeout=httpx.Timeout(self.timeout, connect=min(10.0, self.timeout)),
                    follow_redirects=False,
                    headers=headers,
                ) as client:
                    response = client.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt >= self.max_retries:
                    raise ParaTranzAPIError(
                        f"ParaTranz transport failure ({type(exc).__name__})",
                        retryable=True,
                    ) from exc
                time.sleep(self._retry_delay(None, attempt))
                continue

            if response.status_code in self.RETRYABLE_STATUS_CODES:
                if attempt < self.max_retries:
                    time.sleep(self._retry_delay(response, attempt))
                    continue

            if response.status_code < 200 or response.status_code >= 300:
                message, api_code = self._error_payload(response)
                if self.token:
                    message = message.replace(self.token, "[redacted]")
                raise ParaTranzAPIError(
                    f"ParaTranz request failed: {message}",
                    status_code=response.status_code,
                    api_code=api_code,
                    retryable=response.status_code in self.RETRYABLE_STATUS_CODES,
                )

            if response.status_code == 204:
                return None
            try:
                return response.json()
            except (ValueError, json.JSONDecodeError) as exc:
                raise ParaTranzAPIError(
                    "ParaTranz returned invalid JSON",
                    status_code=response.status_code,
                ) from exc

        raise ParaTranzAPIError("ParaTranz request exhausted retries", retryable=True)

    def list_page(
        self,
        path: str,
        *,
        page: int = 1,
        page_size: int = 100,
        collection_keys: tuple[str, ...] = (),
    ) -> tuple[list[dict], dict]:
        if page < 1:
            raise ValueError("page must be >= 1")
        if not 1 <= page_size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        payload = self.get_json(path, params={"page": page, "pageSize": page_size})
        return _list_payload(payload, collection_keys)

    def list_all(
        self,
        path: str,
        *,
        page_size: int = 100,
        max_pages: int = 100,
        collection_keys: tuple[str, ...] = (),
    ) -> list[dict]:
        if max_pages < 1:
            raise ValueError("max_pages must be >= 1")
        items: list[dict] = []
        seen_ids: set[str] = set()
        previous_signature: str | None = None

        for page in range(1, max_pages + 1):
            batch, metadata = self.list_page(
                path,
                page=page,
                page_size=page_size,
                collection_keys=collection_keys,
            )
            if not batch:
                break

            signature = json.dumps(batch, sort_keys=True, ensure_ascii=False, default=str)
            # Some endpoints/proxies ignore pagination parameters and return
            # the same complete array on every request. Stop instead of looping.
            if signature == previous_signature:
                raise ParaTranzDataError(
                    f"ParaTranz repeated page {page}; refusing to return a partial list"
                )
            previous_signature = signature

            for index, item in enumerate(batch):
                identity = item.get("id")
                key = f"id:{identity}" if identity is not None else f"json:{json.dumps(item, sort_keys=True, ensure_ascii=False, default=str)}"
                if key not in seen_ids:
                    seen_ids.add(key)
                    items.append(item)

            total_pages = next(
                (metadata.get(key) for key in ("pageCount", "page_count", "totalPages", "total_pages", "pages")
                 if isinstance(metadata.get(key), int) and not isinstance(metadata.get(key), bool)),
                None,
            )
            total_rows = next(
                (metadata.get(key) for key in ("rowCount", "total", "totalCount", "total_count", "count")
                 if isinstance(metadata.get(key), int) and not isinstance(metadata.get(key), bool)),
                None,
            )
            if total_pages is not None:
                if page >= total_pages:
                    break
                continue
            if total_rows is not None:
                if len(items) >= total_rows:
                    break
                continue
            if len(batch) < page_size:
                break
        else:
            raise ParaTranzDataError(f"ParaTranz pagination exceeded safety limit ({max_pages} pages)")

        return items


class ParaTranzClient:
    """Read-only project adapter used by project sync and health checks."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.api = ParaTranzAPI(
            settings.paratranz_token,
            base_url=getattr(settings, "paratranz_base_url", ParaTranzAPI.DEFAULT_BASE_URL),
            timeout=getattr(settings, "paratranz_timeout_seconds", 20.0),
            max_retries=getattr(settings, "paratranz_max_retries", 3),
        )

    @staticmethod
    def _project_payload(payload: Any) -> dict:
        payload = _unwrap_data(payload)
        if not isinstance(payload, dict):
            raise ParaTranzDataError("ParaTranz returned a non-object project response")
        return payload

    def project(self) -> dict:
        project_id = _as_nonnegative_int(self.settings.paratranz_project_id, "project_id")
        payload = self._project_payload(self.api.get_json(f"projects/{project_id}"))
        returned_id = payload.get("id")
        if returned_id is not None and _as_nonnegative_int(returned_id, "project.id") != project_id:
            raise ParaTranzDataError("ParaTranz returned a different project than requested")
        return payload

    def files(self) -> list[dict]:
        project_id = _as_nonnegative_int(self.settings.paratranz_project_id, "project_id")
        payload = self.api.get_json(f"projects/{project_id}/files")
        files, _ = _list_payload(payload, ("files",))
        return files

    def members(self, *, page_size: int = 100) -> list[dict]:
        project_id = _as_nonnegative_int(self.settings.paratranz_project_id, "project_id")
        return self.api.list_all(
            f"projects/{project_id}/members",
            page_size=page_size,
            collection_keys=("members", "results", "items"),
        )

    def project_snapshot(self) -> ProjectSnapshot:
        project = self.project()
        files = self.files()
        if not files:
            raise ParaTranzDataError("ParaTranz returned no project files; refusing to publish an empty snapshot")

        required_metrics = ("total", "translated", "reviewed", "words")
        totals = {key: 0 for key in required_metrics}
        for index, item in enumerate(files):
            file_name = item.get("name", str(index))
            for key in required_metrics:
                if key not in item or item[key] is None:
                    raise ParaTranzDataError(
                        f"ParaTranz file {file_name!r} missing metric {key!r}"
                    )
                totals[key] += _as_nonnegative_int(item[key], f"file.{key}")

        if totals["total"] <= 0:
            raise ParaTranzDataError("ParaTranz project contains no strings; refusing to publish an empty snapshot")
        if totals["translated"] > totals["total"] or totals["reviewed"] > totals["total"]:
            raise ParaTranzDataError("ParaTranz project counters exceed total strings")

        raw_members = project.get("members", project.get("memberCount"))
        if isinstance(raw_members, list):
            member_count = len(raw_members)
        elif raw_members is not None:
            member_count = _as_nonnegative_int(raw_members, "members")
        else:
            member_count = len(self.members())

        return ProjectSnapshot(
            project_id=self.settings.paratranz_project_id,
            captured_at=datetime.now(timezone.utc),
            words_total=totals["words"],
            strings_total=totals["total"],
            translated=totals["translated"],
            reviewed=totals["reviewed"],
            files=len(files),
            members=member_count,
        )
