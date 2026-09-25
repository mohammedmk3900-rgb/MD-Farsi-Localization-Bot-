"""Process boundary for deterministic polyglot engines.

Python remains the control plane. Rust performs translation-integrity QA and
Go handles isolated background jobs. Both boundaries use JSON contracts.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class PolyglotEngine:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()

    def _run(self, command: list[str], payload: str) -> dict[str, Any]:
        result = subprocess.run(
            command,
            input=payload,
            text=True,
            capture_output=True,
            check=True,
        )
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise ValueError("polyglot engine returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("polyglot engine returned a non-object")
        return value

    def run_rust_qa(
        self, source: str, target: str, *, binary: str | None = None
    ) -> dict[str, Any]:
        command = [
            binary
            or str(self.root / "genesis/engine/rust/target/debug/mdfarsi-qa")
        ]
        payload = self._run(command, f"{source}\n{target}")
        if payload.get("schema_version") != 1 or payload.get("operation") != "qa":
            raise ValueError("invalid Rust QA contract")
        return payload

    def run_worker(
        self, job: dict[str, Any], *, binary: str | None = None
    ) -> dict[str, Any]:
        command = [
            binary
            or str(self.root / "genesis/engine/go/worker")
        ]
        payload = self._run(
            command, json.dumps(job, ensure_ascii=False, separators=(",", ":"))
        )
        if payload.get("schema_version") != 1 or "operation" not in payload:
            raise ValueError("invalid Go worker contract")
        return payload
