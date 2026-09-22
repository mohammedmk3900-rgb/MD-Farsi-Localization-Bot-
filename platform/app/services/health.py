from __future__ import annotations

from datetime import datetime, timezone

from app.domain.models import HealthStatus


class HealthService:
    def check(self, *, paratranz: bool, discord: bool, database: bool) -> HealthStatus:
        checks = (paratranz, discord, database)
        status = "healthy" if all(checks) else "degraded"
        return HealthStatus(
            status=status,
            checked_at=datetime.now(timezone.utc),
            paratranz=paratranz,
            discord=discord,
            database=database,
        )

    def check_local(self) -> HealthStatus:
        return self.check(paratranz=True, discord=False, database=True)
