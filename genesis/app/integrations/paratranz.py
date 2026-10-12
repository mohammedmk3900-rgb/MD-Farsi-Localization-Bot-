from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
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

    def __post_init__(self) -> None:
        if isinstance(self.project_id, bool) or int(self.project_id) <= 0:
            raise ValueError("ParaTranz project_id must be a positive integer")
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("ParaTranz base URL must be HTTPS and cannot include credentials, query or fragment")
        if float(self.timeout) <= 0:
            raise ValueError("ParaTranz timeout must be positive")
        if isinstance(self.max_retries, bool) or self.max_retries < 0:
            raise ValueError("ParaTranz max_retries cannot be negative")
        if isinstance(self.page_size, bool) or not 1 <= self.page_size <= 1000:
            raise ValueError("ParaTranz page_size must be between 1 and 1000")
        if isinstance(self.max_pages, bool) or self.max_pages < 1:
            raise ValueError("ParaTranz max_pages must be positive")

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
        parsed_base = urlsplit(self.config.base_url)
        if (
            parsed_base.scheme != "https"
            or not parsed_base.hostname
            or parsed_base.username
            or parsed_base.password
            or parsed_base.query
            or parsed_base.fragment
        ):
            raise ValueError("ParaTranz base URL must be HTTPS and cannot include credentials, query or fragment")
        raw_token = token if token is not None else os.getenv("PARATRANZ_TOKEN", "")
        self.token = (raw_token or "").strip()
        if self.token.lower().startswith("bearer "):
            self.token = self.token[7:].strip()
        self.timeout = max(1.0, float(timeout if timeout is not None else self.config.timeout))
        if not self.token:
            # Construction is allowed without a token for offline tooling; the
            # first request fails with a clear, non-secret error.
            self.token = ""

    def _get(self, path: str) -> object:
        if not path or path.startswith(("http://", "https://", "//")) or "\\" in path:
            raise ValueError("ParaTranz path must be relative")
        path_only = path.split("?", 1)[0]
        if any(segment in {".", ".."} for segment in path_only.split("/")):
            raise ValueError("ParaTranz path cannot contain traversal segments")
        if not self.token:
            raise ParaTranzError("PARATRANZ_TOKEN is not configured")
        url = urljoin(self.config.base_url.rstrip("/") + "/", path.lstrip("/"))
        if urlsplit(url).netloc != urlsplit(self.config.base_url).netloc:
            raise ValueError("ParaTranz URL escaped the configured API host")
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
                if self.token:
                    message = message.replace(self.token, "[redacted]")
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
        try:
            payload = self._payload(self._get(f"projects/{self.config.project_id}"))
        except ParaTranzError:
            raise
        except Exception as exc:
            raise ParaTranzError("ParaTranz project request failed") from exc
        if not isinstance(payload, dict):
            raise ParaTranzError("ParaTranz project response is not an object")
        returned_id = payload.get("id")
        if returned_id is not None and self._metric(returned_id, "project.id") != self.config.project_id:
            raise ParaTranzError("ParaTranz returned a different project than requested")
        return payload

    def files(self) -> list[dict]:
        try:
            payload = self._get(f"projects/{self.config.project_id}/files")
        except ParaTranzError:
            raise
        except Exception as exc:
            raise ParaTranzError("ParaTranz files request failed") from exc
        files, _ = self._list_payload(payload, ("files",))
        return files

    def _list_all(
        self,
        path: str,
        keys: tuple[str, ...],
        *,
        page_size: int | None = None,
        params: dict[str, object] | None = None,
    ) -> list[dict]:
        size = page_size or self.config.page_size
        if not 1 <= size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        items: list[dict] = []
        seen: set[str] = set()
        previous_signature: str | None = None
        for page in range(1, self.config.max_pages + 1):
            query_values = {"page": page, "pageSize": size, **(params or {})}
            query = urlencode(query_values)
            try:
                payload = self._get(f"{path}?{query}")
            except ParaTranzError:
                raise
            except Exception as exc:
                raise ParaTranzError("ParaTranz list request failed") from exc
            batch, metadata = self._list_payload(payload, keys)
            if not batch:
                break
            signature = json.dumps(batch, sort_keys=True, ensure_ascii=False, default=str)
            if signature == previous_signature:
                raise ParaTranzError("ParaTranz repeated a page; refusing to return a partial list")
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
            if len(batch) < size:
                break
        else:
            raise ParaTranzError("ParaTranz pagination exceeded safety limit")
        return items

    _COLLECTIONS = {
        "files": ("files", "results", "items"),
        "members": ("members", "results", "items"),
        "terms": ("terms", "results", "items"),
        "scores": ("scores", "results", "items"),
        "strings": ("strings", "results", "items"),
        "history": ("history", "results", "items"),
        "issues": ("issues", "results", "items"),
        "artifacts": ("artifacts", "results", "items"),
    }

    @staticmethod
    def _resource_id(value: int | str, field: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{field} must be a positive integer")
        try:
            result = int(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"{field} must be a positive integer") from exc
        if result <= 0 or str(result) != str(value).strip():
            raise ValueError(f"{field} must be a positive integer")
        return result

    def list_resource(
        self,
        resource: str,
        *,
        page: int = 1,
        page_size: int | None = None,
        all_pages: bool = False,
        params: dict[str, object] | None = None,
    ) -> list[dict] | tuple[list[dict], dict]:
        """Read an allow-listed project collection without exposing write routes."""
        if resource not in self._COLLECTIONS:
            raise ValueError(f"Unsupported read-only ParaTranz collection: {resource}")
        if page < 1:
            raise ValueError("page must be >= 1")
        size = page_size or self.config.page_size
        if not 1 <= size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        path = f"projects/{self._resource_id(self.config.project_id, 'project_id')}/{resource}"
        keys = self._COLLECTIONS[resource]
        if all_pages:
            return self._list_all(path, keys, page_size=size, params=params)
        query = {"page": page, "pageSize": size, **(params or {})}
        payload = self._get(f"{path}?{urlencode(query)}")
        return self._list_payload(payload, keys)

    def list_projects(self, *, page: int = 1, page_size: int | None = None) -> tuple[list[dict], dict]:
        if page < 1:
            raise ValueError("page must be >= 1")
        size = page_size or self.config.page_size
        if not 1 <= size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        payload = self._get(f"projects?{urlencode({'page': page, 'pageSize': size})}")
        return self._list_payload(payload, ("projects", "results", "items"))

    def file(self, file_id: int | str) -> dict:
        payload = self._payload(self._get(
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/files/{self._resource_id(file_id, 'file_id')}"
        ))
        if not isinstance(payload, dict):
            raise ParaTranzError("ParaTranz file response is not an object")
        return payload

    def file_translation(self, file_id: int | str) -> object:
        return self._get(
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/files/{self._resource_id(file_id, 'file_id')}/translation"
        )

    def term(self, term_id: int | str) -> dict:
        payload = self._payload(self._get(
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/terms/{self._resource_id(term_id, 'term_id')}"
        ))
        if not isinstance(payload, dict):
            raise ParaTranzError("ParaTranz term response is not an object")
        return payload

    def string(self, string_id: int | str) -> dict:
        payload = self._payload(self._get(
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/strings/{self._resource_id(string_id, 'string_id')}"
        ))
        if not isinstance(payload, dict):
            raise ParaTranzError("ParaTranz string response is not an object")
        return payload

    def latest_artifact(self) -> object:
        return self._get(
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/artifacts/latest"
        )

    def file_revisions(self, *, page: int = 1, page_size: int | None = None, params: dict[str, object] | None = None) -> tuple[list[dict], dict]:
        if page < 1:
            raise ValueError("page must be >= 1")
        size = page_size or self.config.page_size
        if not 1 <= size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        project_id = self._resource_id(self.config.project_id, "project_id")
        query = {"page": page, "pageSize": size, **(params or {})}
        payload = self._get(f"projects/{project_id}/files/revisions?{urlencode(query)}")
        return self._list_payload(payload, ("revisions", "history", "results", "items"))

    def artifact(self, artifact_id: int | str) -> dict:
        payload = self._payload(self._get(
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/artifacts/{self._resource_id(artifact_id, 'artifact_id')}"
        ))
        if not isinstance(payload, dict):
            raise ParaTranzError("ParaTranz artifact response is not an object")
        return payload

    def term_history(self, term_id: int | str, *, page: int = 1, page_size: int | None = None) -> tuple[list[dict], dict]:
        if page < 1:
            raise ValueError("page must be >= 1")
        size = page_size or self.config.page_size
        if not 1 <= size <= 1000:
            raise ValueError("page_size must be between 1 and 1000")
        path = (
            f"projects/{self._resource_id(self.config.project_id, 'project_id')}/terms/"
            f"{self._resource_id(term_id, 'term_id')}/history"
        )
        payload = self._get(f"{path}?{urlencode({'page': page, 'pageSize': size})}")
        return self._list_payload(payload, ("history", "results", "items"))

    def members(self) -> list[dict]:
        return self._list_all(f"projects/{self.config.project_id}/members", ("members", "results", "items"))

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
        elif isinstance(raw_members, (int, float, str)) and not isinstance(raw_members, bool):
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
