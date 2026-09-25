from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.domain.permissions import allowed


@dataclass(frozen=True)
class DiscordActor:
    user_id: str
    roles: tuple[str, ...] = ()


class DiscordCommandError(RuntimeError):
    pass


class DiscordCommandGateway:
    """Transport-neutral command gateway for a Discord slash-command adapter."""

    def __init__(self, application, permission_check: Callable[[DiscordActor, str], bool] | None = None):
        self.application = application
        self.permission_check = permission_check or self._default_permission_check

    @staticmethod
    def _default_permission_check(actor: DiscordActor, permission: str) -> bool:
        return any(allowed(role, permission) for role in actor.roles)

    def authorize(self, actor: DiscordActor, permission: str) -> None:
        if not self.permission_check(actor, permission):
            raise DiscordCommandError(f"permission denied: {permission}")

    def health(self, actor: DiscordActor):
        self.authorize(actor, "health.read")
        return self.application.health.evaluate({
            "store": "ok",
            "translation": "ok",
            "glossary": "ok",
        })

    def tasks(self, actor: DiscordActor):
        self.authorize(actor, "tasks.self")
        return self.application.tasks.list()

    def check_translation(self, actor: DiscordActor, source: str, translation: str):
        self.authorize(actor, "translation.check")
        return self.application.translation.check(source, translation, self.application.glossary.all())

    def create_task(self, actor: DiscordActor, title: str, scope: str = "", priority: str = "normal"):
        self.authorize(actor, "tasks.manage")
        from app.domain.models import Priority
        return self.application.tasks.create(title=title, scope=scope, priority=Priority(priority))

    def sync(self, actor: DiscordActor, integration):
        self.authorize(actor, "sync.run")
        return self.application.sync.project(self.application, integration)
