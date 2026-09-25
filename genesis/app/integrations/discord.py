from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.domain.permissions import allowed


@dataclass(frozen=True)
class DiscordActor:
    user_id: str
    roles: tuple[str, ...] = ()


class DiscordCommandError(RuntimeError):
    pass


class DiscordCommandGateway:
    """Authorization and command boundary; contains no Discord SDK dependency."""

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
        return self.application.health.evaluate({"store": "ok", "translation": "ok", "glossary": "ok"})

    def tasks(self, actor: DiscordActor):
        self.authorize(actor, "tasks.self")
        return self.application.tasks.list()

    def review_queue(self, actor: DiscordActor):
        self.authorize(actor, "translation.check")
        return self.application.command_center.review_queue()

    def command_center(self, actor: DiscordActor):
        self.authorize(actor, "project.read")
        return self.application.command_center.status()

    def check_translation(self, actor: DiscordActor, source: str, translation: str):
        self.authorize(actor, "translation.check")
        return self.application.translation.check(source, translation, self.application.glossary.all())

    def create_task(self, actor: DiscordActor, title: str, scope: str = "", priority: str = "normal", due_at: str | None = None):
        self.authorize(actor, "tasks.manage")
        from app.domain.models import Priority
        return self.application.tasks.create(title=title, scope=scope, priority=Priority(priority), due_at=due_at)

    def claim_task(self, actor: DiscordActor, task_id: int):
        self.authorize(actor, "tasks.self")
        return self.application.tasks.claim(self.application.tasks.get(task_id), actor.user_id)

    def submit_task(self, actor: DiscordActor, task_id: int):
        self.authorize(actor, "tasks.self")
        return self.application.tasks.submit(self.application.tasks.get(task_id), actor.user_id)

    def approve_task(self, actor: DiscordActor, task_id: int):
        self.authorize(actor, "tasks.manage")
        return self.application.tasks.complete(self.application.tasks.get(task_id), actor.user_id)

    def sync(self, actor: DiscordActor, integration):
        self.authorize(actor, "sync.run")
        return self.application.sync.project(self.application, integration)


@dataclass(frozen=True)
class DiscordCommand:
    name: str
    permission: str


class DiscordTransport:
    """Final transport adapter contract. A Discord SDK can call dispatch()."""

    COMMANDS = {
        "health": DiscordCommand("health", "health.read"),
        "status": DiscordCommand("status", "project.read"),
        "tasks": DiscordCommand("tasks", "tasks.self"),
        "review": DiscordCommand("review", "translation.check"),
    }

    def __init__(self, gateway: DiscordCommandGateway):
        self.gateway = gateway

    def dispatch(self, actor: DiscordActor, command: str, **kwargs: Any) -> Any:
        spec = self.COMMANDS.get(command)
        if spec is None:
            raise DiscordCommandError(f"unknown command: {command}")
        self.gateway.authorize(actor, spec.permission)
        if command == "health":
            return self.gateway.health(actor)
        if command == "status":
            return self.gateway.command_center(actor)
        if command == "tasks":
            return self.gateway.tasks(actor)
        if command == "review":
            return self.gateway.review_queue(actor)
        raise DiscordCommandError(f"unsupported command: {command}")
