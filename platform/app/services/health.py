from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import HealthStatus


class HealthService:
    def check(self, *, paratranz: bool, discord: bool, database: bool) -> HealthStatus:
        status = "healthy" if all((paratranz, discord, database)) else "degraded"
        return HealthStatus(
            status=status,
            checked_at=datetime.now(timezone.utc),
            paratranz=paratranz,
            discord=discord,
            database=database,
        )
