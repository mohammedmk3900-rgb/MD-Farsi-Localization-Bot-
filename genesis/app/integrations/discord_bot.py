from __future__ import annotations

import os

from app.integrations.discord import DiscordActor, DiscordCommandAdapter, DiscordCommandGateway
from app.integrations.paratranz import ParaTranzIntegration
from app.runtime import build_application


def _actor(interaction) -> DiscordActor:
    # Discord role names are normalized to the domain permission identifiers.
    roles = tuple(
        role.name.strip().lower().replace(" ", "_").replace("-", "_")
        for role in getattr(interaction.user, "roles", ())
    )
    return DiscordActor(str(interaction.user.id), roles)


def build_bot():
    """Create the real discord.py slash-command transport around the Genesis core."""
    try:
        import discord
        from discord import app_commands
    except ImportError as exc:
        raise RuntimeError("Install the project dependencies to run the Discord bot") from exc

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)
    application = build_application()
    gateway = DiscordCommandGateway(application)
    adapter = DiscordCommandAdapter(gateway)
    paratranz = ParaTranzIntegration()

    @tree.command(name="genesis-health", description="Show V11 Genesis service health")
    async def genesis_health(interaction: discord.Interaction):
        try:
            report = adapter.dispatch(_actor(interaction), "health")
            checks = "\n".join(f"• {key}: {value}" for key, value in report.checks.items())
            await interaction.response.send_message(f"**Genesis: {report.status.upper()}**\n{checks}", ephemeral=True)
        except Exception as exc:
            await interaction.response.send_message(f"خطا: {exc}", ephemeral=True)

    @tree.command(name="genesis-tasks", description="List Genesis tasks")
    async def genesis_tasks(interaction: discord.Interaction):
        try:
            tasks = adapter.dispatch(_actor(interaction), "tasks")
            if not tasks:
                message = "فعلاً مأموریتی ثبت نشده."
            else:
                message = "\n".join(f"#{task.id} · {task.status.value} · {task.title}" for task in tasks[:15])
            await interaction.response.send_message(message[:1900], ephemeral=True)
        except Exception as exc:
            await interaction.response.send_message(f"خطا: {exc}", ephemeral=True)

    @tree.command(name="genesis-check", description="Run deterministic translation QA")
    @app_commands.describe(source="Original source text", translation="Persian translation")
    async def genesis_check(interaction: discord.Interaction, source: str, translation: str):
        try:
            result = adapter.dispatch(_actor(interaction), "check", source=source, translation=translation)
            findings = result.findings
            if findings:
                body = "\n".join(f"• {item.get('kind', 'finding')}: {item.get('message', item)}" for item in findings[:8])
            else:
                body = "بررسی فنی اولیه مشکلی پیدا نکرد؛ تأیید انسانی همچنان الزامی است."
            await interaction.response.send_message(body[:1900], ephemeral=True)
        except Exception as exc:
            await interaction.response.send_message(f"خطا: {exc}", ephemeral=True)

    @tree.command(name="genesis-sync", description="Synchronize authoritative ParaTranz stats and glossary")
    async def genesis_sync(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            result = adapter.dispatch(_actor(interaction), "sync", integration=paratranz)
            await interaction.followup.send(
                f"✅ Sync موفق\nProject: {result['project_id']}\n"
                f"Translated: {result['translated']} · Reviewed: {result['reviewed']}\n"
                f"Glossary: {result['glossary_terms']} terms\nRun: {result['run_id']}",
                ephemeral=True,
            )
        except Exception as exc:
            await interaction.followup.send(f"❌ Sync ناموفق: {exc}", ephemeral=True)

    @client.event
    async def on_ready():
        await tree.sync()
        print(f"V11 Genesis Discord transport ready as {client.user}")

    return client


def main() -> None:
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    build_bot().run(token)


if __name__ == "__main__":
    main()
