from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProjectSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    project_id: int
    captured_at: datetime
    words_total: int = Field(ge=0)
    strings_total: int = Field(ge=0)
    translated: int = Field(ge=0)
    reviewed: int = Field(ge=0)
    files: int = Field(ge=0)
    members: int = Field(ge=0)

    @property
    def translation_percent(self) -> float:
        return (self.translated / self.strings_total * 100) if self.strings_total else 0.0

    @property
    def review_percent(self) -> float:
        return (self.reviewed / self.strings_total * 100) if self.strings_total else 0.0


class DiscordSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    captured_at: datetime
    guild_id: str
    guild_name: str
    categories: int = 0
    channels: int = 0
    roles: int = 0
    sampled_messages: int = 0
    active_channels: int = 0


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    checked_at: datetime
    paratranz: bool
    discord: bool
    database: bool


class CommandCenterSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    captured_at: datetime
    project: ProjectSnapshot
    discord: DiscordSnapshot | None = None
    health: HealthStatus
