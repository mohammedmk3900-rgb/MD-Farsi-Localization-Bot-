from __future__ import annotations

import json

import discord
from discord import app_commands

from app.application import application
from app.services.commands import CommandService

commands = CommandService()
intents = discord.Intents.none()
intents.guilds = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


def render(data: object) -> str:
    return "json\n" + json.dumps(data, ensure_ascii=False, indent=2)[:1900]


@bot.event
async def on_ready():
    application.record("discord.ready", {
        "guild_id": application.context.settings.discord_guild_id,
        "connected": True,
    })
    await tree.sync()


project = app_commands.Group(name="project", description="MD Farsi Localization project")


@project.command(name="status", description="نمایش وضعیت سامانه")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.status()), ephemeral=True)


@project.command(name="stats", description="نمایش آخرین آمار ذخیره‌شده")
async def stats(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.stats()), ephemeral=True)


@project.command(name="progress", description="نمایش آخرین پیشرفت ذخیره‌شده")
async def progress(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.progress()), ephemeral=True)


@project.command(name="glossary", description="واژه‌نامه زنده ParaTranz")
async def glossary(interaction: discord.Interaction, page: int = 1):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(render(commands.glossary(page)), ephemeral=True)


@project.command(name="history", description="تاریخچه Snapshotها")
async def history(interaction: discord.Interaction, limit: int = 10):
    await interaction.response.send_message(render(commands.history(limit)), ephemeral=True)


@project.command(name="health", description="سلامت سامانه")
async def health(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.health()), ephemeral=True)


@project.command(name="achievements", description="نقاط عطف پروژه")
async def achievements(interaction: discord.Interaction):
    await interaction.response.send_message(render(commands.achievements()), ephemeral=True)


@project.command(name="sync", description="همگام‌سازی مستقیم با ParaTranz")
async def sync(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(render(commands.sync()), ephemeral=True)


@project.command(name="report", description="گزارش پروژه")
@app_commands.describe(period="daily یا weekly")
async def report(interaction: discord.Interaction, period: str = "daily"):
    if period not in {"daily", "weekly"}:
        await interaction.response.send_message("period باید daily یا weekly باشد.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await interaction.followup.send(render(commands.report(period)), ephemeral=True)


@project.command(name="help", description="فهرست فرمان‌های پروژه")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("\n".join(commands.help()), ephemeral=True)


tree.add_command(project)


def run() -> None:
    token = application.context.settings.discord_bot_token
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    bot.run(token)
