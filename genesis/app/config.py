from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GenesisConfig:
    """Immutable runtime configuration; secrets are never persisted by Genesis."""

    project_id: int = 19621
    database_path: Path = Path("data/genesis.sqlite3")
    environment: str = "development"
    busy_timeout_ms: int = 5000
    event_retention: int = 1000

    @classmethod
    def from_env(cls) -> "GenesisConfig":
        project_id = int(os.getenv("PARATRANZ_PROJECT_ID", "19621"))
        database_path = Path(os.getenv("GENESIS_DATABASE", "data/genesis.sqlite3"))
        environment = os.getenv("GENESIS_ENV", "development").strip().lower() or "development"
        return cls(
            project_id=project_id,
            database_path=database_path,
            environment=environment,
            busy_timeout_ms=max(100, int(os.getenv("GENESIS_SQLITE_BUSY_TIMEOUT_MS", "5000"))),
            event_retention=max(100, int(os.getenv("GENESIS_EVENT_RETENTION", "1000"))),
        )
