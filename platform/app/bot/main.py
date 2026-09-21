from __future__ import annotations

import discord
from discord import app_commands

from app.application import application
from app.services.commands import CommandService


commands = CommandService()
intents = discord.Intents.none()
intents.guilds = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


@bot.event
async def on_ready():
    application.record(
        "discord.ready",
        {
            "guild_id": application.context.settings.discord_guild_id,
            "connected": True,
        },
    )
    await tree.sync()


project = app_commands.Group(name="project", description="MD Farsi Localization project")


@project.command(name="status", description="نمایش وضعیت سامانه")
async def status(interaction: discord.Interaction):
    await interaction.response.send_message(str(commands.status()), ephemeral=True)


@project.command(name="health", description="بررسی سلامت سامانه")
async def health(interaction: discord.Interaction):
    await interaction.response.send_message(str(commands.health()), ephemeral=True)


@project.command(name="help", description="فهرست فرمان‌های پروژه")
async def help_command(interaction: discord.Interaction):
    await interaction.response.send_message("\n".join(commands.help()), ephemeral=True)


tree.add_command(project)


def run() -> None:
    token = application.context.settings.discord_bot_token
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    bot.run(token)
