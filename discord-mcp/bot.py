"""Discord Gateway indexer: backfill authorized history and keep SQLite current."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import discord
from dotenv import load_dotenv

from indexer import MessageIndex

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
DB_PATH = os.getenv("DISCORD_DB_PATH", "/app/data/discord.db")
BACKFILL_ON_START = os.getenv("DISCORD_BACKFILL_ON_START", "true").lower() in {"1", "true", "yes", "on"}
BACKFILL_CONCURRENCY = max(1, int(os.getenv("DISCORD_BACKFILL_CONCURRENCY", "2")))

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("discord-indexer")

if not TOKEN or not GUILD_ID:
    raise RuntimeError("DISCORD_BOT_TOKEN and DISCORD_GUILD_ID are required")

index = MessageIndex(DB_PATH)


def serialize(message: discord.Message) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "channel_id": str(message.channel.id),
        "channel_name": getattr(message.channel, "name", None),
        "author_id": str(message.author.id) if message.author else None,
        "author_name": getattr(message.author, "global_name", None) or getattr(message.author, "name", None),
        "content": message.content or "",
        "timestamp": message.created_at.isoformat(),
        "edited_timestamp": message.edited_at.isoformat() if message.edited_at else None,
        "url": message.jump_url,
    }


def is_indexable(channel: object) -> bool:
    return isinstance(channel, (discord.TextChannel, discord.ForumChannel, discord.Thread))


class IndexerBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self._backfill_started = False

    async def on_ready(self) -> None:
        guild = self.get_guild(GUILD_ID)
        if guild is None:
            log.error("Guild %s is not visible to the bot; check guild ID and membership.", GUILD_ID)
            return

        log.info("Connected as %s; guild=%s (%s)", self.user, guild.name, guild.id)
        if BACKFILL_ON_START and not self._backfill_started:
            self._backfill_started = True
            asyncio.create_task(self.backfill_guild(guild))

    async def backfill_guild(self, guild: discord.Guild) -> None:
        channels = [channel for channel in guild.channels if is_indexable(channel)]
        log.info("Starting automatic backfill: %d channels", len(channels))
        sem = asyncio.Semaphore(BACKFILL_CONCURRENCY)

        async def one(channel: object) -> None:
            async with sem:
                try:
                    await self.backfill_channel(channel)  # type: ignore[arg-type]
                except (discord.Forbidden, discord.NotFound) as exc:
                    log.warning("Skipping inaccessible channel %s: %s", getattr(channel, "id", "?"), exc)
                except discord.HTTPException as exc:
                    log.warning("Discord API error for channel %s: %s", getattr(channel, "id", "?"), exc)
                except Exception:
                    log.exception("Unexpected backfill error for channel %s", getattr(channel, "id", "?"))

        await asyncio.gather(*(one(channel) for channel in channels))
        log.info("Automatic backfill finished; indexed_messages=%d", index.count())

    async def backfill_channel(self, channel: discord.abc.Messageable) -> None:
        channel_id = str(channel.id)
        cursor = index.get_cursor(channel_id) or {}
        newest_id = cursor.get("newest_message_id")
        oldest_id = cursor.get("oldest_message_id")
        complete = bool(cursor.get("complete"))
        total = 0

        if complete and newest_id:
            after = discord.Object(id=int(newest_id))
            async for message in channel.history(limit=None, after=after, oldest_first=True):
                item = serialize(message)
                index.upsert_messages([item])
                index.set_cursor(channel_id, newest_message_id=item["id"], complete=True)
                total += 1
            log.info("Incremental sync #%s: %d new messages", getattr(channel, "name", channel.id), total)
            return

        before = discord.Object(id=int(oldest_id)) if oldest_id else None
        newest = newest_id
        oldest = oldest_id

        async for message in channel.history(limit=None, before=before, oldest_first=False):
            item = serialize(message)
            index.upsert_messages([item])
            total += 1
            if newest is None:
                newest = item["id"]
            oldest = item["id"]

        index.set_cursor(channel_id, newest_message_id=newest, oldest_message_id=oldest, complete=True)
        log.info("Historical sync #%s: %d messages", getattr(channel, "name", channel.id), total)

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        index.upsert_messages([serialize(message)])
        channel_id = str(message.channel.id)
        cursor = index.get_cursor(channel_id) or {}
        index.set_cursor(
            channel_id,
            newest_message_id=str(message.id),
            oldest_message_id=cursor.get("oldest_message_id"),
            complete=bool(cursor.get("complete")),
        )

    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if after.guild is None or after.guild.id != GUILD_ID:
            return
        index.upsert_messages([serialize(after)])

    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.guild.id != GUILD_ID:
            return
        index.mark_deleted(str(message.id))


async def main() -> None:
    bot = IndexerBot()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
