from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Alert:
    severity: str
    component: str
    message: str


class AlertService:
    def service_failure(self, component: str, message: str) -> Alert:
        return Alert("critical", component, message)

    def degraded(self, component: str, message: str) -> Alert:
        return Alert("warning", component, message)
