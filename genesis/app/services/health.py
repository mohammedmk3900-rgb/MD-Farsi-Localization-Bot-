from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: dict[str, str]


class HealthService:
    def evaluate(self, checks: dict[str, str]) -> HealthReport:
        status = "ok" if all(value == "ok" for value in checks.values()) else "degraded"
        return HealthReport(status=status, checks=dict(checks))
