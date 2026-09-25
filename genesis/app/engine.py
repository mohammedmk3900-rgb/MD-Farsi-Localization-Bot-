from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from urllib import error, request


@dataclass(frozen=True)
class RustCheckResult:
    missing: tuple[str, ...]
    unexpected: tuple[str, ...]


class RustEngineClient:
    """Process boundary for deterministic Rust translation analysis."""

    def __init__(self, executable: str):
        self.executable = executable

    @classmethod
    def from_env(cls) -> "RustEngineClient | None":
        path = os.getenv("GENESIS_RUST_ENGINE")
        return cls(path) if path else None

    def check_translation(self, source: str, translation: str) -> RustCheckResult:
        payload = json.dumps({"source": source, "translation": translation})
        completed = subprocess.run(
            [self.executable],
            input=payload,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        result = json.loads(completed.stdout)
        return RustCheckResult(
            missing=tuple(result.get("missing", [])),
            unexpected=tuple(result.get("unexpected", [])),
        )


class GoWorkerClient:
    """HTTP boundary for long-lived concurrent Go workers."""

    def __init__(self, base_url: str, timeout: float = 3.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @classmethod
    def from_env(cls) -> "GoWorkerClient | None":
        url = os.getenv("GENESIS_GO_URL")
        return cls(url) if url else None

    def health(self) -> dict:
        with request.urlopen(f"{self.base_url}/health", timeout=self.timeout) as response:
            return json.load(response)

    def submit(self, job_type: str, payload: dict) -> dict:
        body = json.dumps({"type": job_type, "payload": payload}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/jobs",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.load(response)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Go worker rejected job: {detail}") from exc
