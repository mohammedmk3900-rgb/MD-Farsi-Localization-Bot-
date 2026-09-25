"""Thin process boundary between Python and deterministic polyglot engines."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path


class PolyglotEngine:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or Path.cwd()).resolve()

    def run_rust_qa(self, source: str, target: str, *, binary: str | None = None) -> dict:
        command = [binary or str(self.root / "genesis/engine/rust/target/debug/mdfarsi-qa")]
        result = subprocess.run(command, input=f"{source}\n{target}", text=True, capture_output=True, check=True)
        payload = json.loads(result.stdout)
        if payload.get("schema_version") != 1 or payload.get("operation") != "qa":
            raise ValueError("invalid Rust QA contract")
        return payload

    def run_worker(self, job: dict, *, binary: str | None = None) -> dict:
        command = [binary or str(self.root / "genesis/engine/go/worker")]
        result = subprocess.run(command, input=json.dumps(job, ensure_ascii=False), text=True, capture_output=True, check=True)
        payload = json.loads(result.stdout)
        if payload.get("schema_version") != 1 or "operation" not in payload:
            raise ValueError("invalid Go worker contract")
        return payload
