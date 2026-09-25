from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DiscordCommand:
    name: str
    permission: str
    handler: Callable[..., object]


class DiscordGateway:
    """Transport-neutral command registry for the future Discord adapter."""

    def __init__(self) -> None:
        self._commands: dict[str, DiscordCommand] = {}

    def register(self, name: str, permission: str, handler: Callable[..., object]) -> None:
        if name in self._commands:
            raise ValueError(f"command already registered: {name}")
        self._commands[name] = DiscordCommand(name, permission, handler)

    def command(self, name: str) -> DiscordCommand:
        try:
            return self._commands[name]
        except KeyError as exc:
            raise KeyError(f"unknown command: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._commands)
