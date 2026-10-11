from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: dict[str, str]
    checked_at: str


class HealthService:
    def evaluate(self, checks: dict[str, str]) -> HealthReport:
        status = "ok" if checks and all(value == "ok" for value in checks.values()) else "degraded"
        return HealthReport(status=status, checks=dict(checks), checked_at=datetime.now(timezone.utc).isoformat())

    def database(self, store) -> str:
        try:
            with store._connect() as db:
                db.execute("SELECT 1").fetchone()
            return "ok"
        except Exception:
            return "degraded"

    def snapshot(self, store) -> dict:
        return {"database": self.database(store), "checked_at": datetime.now(timezone.utc).isoformat()}
