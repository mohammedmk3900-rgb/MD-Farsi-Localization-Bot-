# Discord MCP — Read-Only Automatic History Bridge

Discord Gateway + MCP service for the Millennium Dawn Farsi Localization server.

## Architecture

Discord Server → Discord Bot Gateway → SQLite History Index → Remote MCP → ChatGPT

The service automatically performs an initial/resumable history backfill and then keeps the index current from Discord Gateway events.

## Automatic behavior

- New message → indexed automatically.
- Edited message → indexed version updated.
- Deleted message → retained as a deletion tombstone and excluded from search.
- Restart → resumes historical work or performs incremental catch-up.
- SQLite WAL → bot and MCP can safely share the database.
- Discord permissions remain authoritative; inaccessible channels are skipped.

## MCP tools

- get_server_overview
- list_channels
- sync_channel_history
- sync_server_history
- get_sync_status
- search_index
- read_channel

## Configuration

Required environment variables:

- DISCORD_BOT_TOKEN
- DISCORD_GUILD_ID
- MCP_HOST (default 0.0.0.0)
- MCP_PORT (default 8000)
- DISCORD_DB_PATH (default /app/data/discord.db)
- DISCORD_BACKFILL_ON_START (default true)
- DISCORD_BACKFILL_CONCURRENCY (default 2)
- LOG_LEVEL (default INFO)

Never commit a real bot token.

## Discord permissions

The bot must be able to view the target channels and read message history. Enable Message Content Intent in the Discord Developer Portal.

## Docker

The container runs both the Discord Gateway indexer and the MCP server. Persist /app/data so the SQLite history survives restarts. Put the MCP endpoint behind HTTPS before connecting a remote client.

## Security

The project intentionally exposes read-only MCP capabilities. It does not send messages, moderate, change roles, or bypass Discord permissions.
