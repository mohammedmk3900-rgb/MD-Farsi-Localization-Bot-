from __future__ import annotations

LEGACY_WORKFLOWS = (
    "glossary-sync.yml",
    "command-center-reports.yml",
    "platform-v9.yml",
)

LEGACY_WEBHOOK_ENV = (
    "DISCORD_WEBHOOK_URL",
    "DISCORD_PROGRESS_WEBHOOK_URL",
    "DISCORD_ACHIEVEMENTS_WEBHOOK_URL",
    "DISCORD_HEALTH_WEBHOOK_URL",
    "DISCORD_REPORTS_WEBHOOK_URL",
    "DISCORD_GLOSSARY_WEBHOOK_URL",
)


class LegacyMigration:
    """Tracks the clean-room migration boundary before destructive cleanup."""

    replacement = "platform + MD news Bot API"

    @classmethod
    def manifest(cls) -> dict:
        return {
            "legacy_webhooks": list(cls.LEGACY_WEBHOOK_ENV),
            "legacy_workflows": list(cls.LEGACY_WORKFLOWS),
            "replacement": cls.replacement,
            "policy": "dual-read, single-write, validate, then remove",
        }
