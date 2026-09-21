# Discord MCP — Read-Only Automatic History Bridge

This component gives the project a read-only bridge from the **Millennium Dawn Farsi Localization Discord server** to an MCP client such as ChatGPT.

## Architecture

Discord Server → Discord Bot Gateway → SQLite History Index → MCP Server → ChatGPT

The bot respects Discord permissions. It can only index channels and messages that the bot account can access.

## What it can inspect

- 🏛️ Server name, ID and owner ID
- 📁 All visible categories and channels
- 🔐 Channel permission overwrites returned by Discord
- 👥 Server roles and permission bitsets
- 💬 Message history from accessible text channels
- 🔎 Full-text search over indexed messages
- 📊 Sync/index status

## Automatic behavior

- New message → indexed automatically.
- Edited message → indexed version updated.
- Deleted message → retained as a deletion tombstone and excluded from search.
- Restart → resumes historical work or performs incremental catch-up.
- SQLite WAL → bot and MCP share the same database.
- Inaccessible channels → skipped; Discord permissions remain authoritative.

## MCP tools

- `get_server_overview` — complete visible server summary
- `list_channels` — categories/channels + permission overwrites
- `list_roles` — server roles + permission bitsets
- `sync_channel_history` — sync one accessible channel
- `sync_server_history` — sync all accessible text channels
- `get_sync_status` — index status
- `search_index` — search indexed messages
- `read_channel` — read indexed channel history

## Configuration

Required:

- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`

Optional:

- `MCP_HOST` (default `0.0.0.0`)
- `MCP_PORT` (default `8000`)
- `DISCORD_DB_PATH` (default `/app/data/discord.db`)
- `DISCORD_BACKFILL_ON_START` (default `true`)
- `DISCORD_BACKFILL_CONCURRENCY` (default `2`)
- `LOG_LEVEL` (default `INFO`)

**Never commit a real bot token.**

## Discord configuration

The bot needs permission to view target channels and read message history. Enable **Message Content Intent** in the Discord Developer Portal.

The MCP endpoint should be placed behind HTTPS before connecting a remote client.

## Privacy and scope

This bridge is intentionally **read-only**. It does not send messages, moderate, change roles, or bypass Discord permissions. It is intended to let an authorized MCP client inspect the server so project management can be based on the actual Discord state rather than screenshots or copied text.
