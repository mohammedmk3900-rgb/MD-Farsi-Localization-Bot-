from __future__ import annotations

import discord
from discord.ext import commands

from app.config import settings


intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = False

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"MD news connected as {bot.user} • guilds={len(bot.guilds)}")


@bot.command(name="health")
async def health(ctx: commands.Context):
    await ctx.send("MD Farsi Localization Platform: operational")


def run() -> None:
    if not settings.discord_bot_token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    bot.run(settings.discord_bot_token)
