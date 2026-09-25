from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.domain.permissions import Permission


@dataclass(frozen=True)
class DiscordActor:
    user_id: str
    roles: tuple[str, ...] = ()


class DiscordCommandError(RuntimeError):
    pass


class DiscordCommandGateway:
    """Transport-neutral command gateway for a Discord adapter.

    A real Discord library can bind slash commands to these methods without
    coupling Discord objects to Genesis domain services.
    """

    def __init__(self, application, permission_check: Callable[[DiscordActor, Permission], bool]):
        self.application = application
        self.permission_check = permission_check

    def authorize(self, actor: DiscordActor, permission: Permission) -> None:
        if not self.permission_check(actor, permission):
            raise DiscordCommandError(f"permission denied: {permission.value}")

    def health(self, actor: DiscordActor):
        self.authorize(actor, Permission.HEALTH_READ)
        return self.application.health.evaluate()

    def tasks(self, actor: DiscordActor):
        self.authorize(actor, Permission.TASKS_SELF)
        return self.application.tasks.list()

    def check_translation(self, actor: DiscordActor, source: str, translation: str):
        self.authorize(actor, Permission.TRANSLATION_CHECK)
        return self.application.translation.check(source, translation, self.application.glossary.all())

    def create_task(self, actor: DiscordActor, title: str, scope: str = "", priority: str = "normal"):
        self.authorize(actor, Permission.TASKS_MANAGE)
        return self.application.tasks.create(title=title, scope=scope, priority=priority)

    def sync(self, actor: DiscordActor, integration):
        self.authorize(actor, Permission.SYNC_RUN)
        return self.application.sync.project(self.application, integration)
