from __future__ import annotations

from app.services.dashboard import DashboardService


class PublicExportService:
    def __init__(self, database):
        self.database = database
        self.dashboard = DashboardService()

    def latest(self) -> dict:
        rows = self.database.recent_snapshots(1)
        if not rows:
            return {"schema": 1, "available": False}
        return {"available": True, **self.dashboard.public_contract(rows[0]["payload"])}
