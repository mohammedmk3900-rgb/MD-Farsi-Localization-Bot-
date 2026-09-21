# ChatGPT Free — Discord Audit Bridge

The live Discord MCP remains useful for MCP-capable clients. For ChatGPT Free, this repository also maintains a sanitized audit snapshot automatically.

## Flow

Discord API → GitHub Actions → `data/discord_audit.json` → ChatGPT Free

The snapshot runs every 6 hours and can be triggered manually.

## Included

- server name and structural counts
- categories and channels
- channel hierarchy and permission-overwrite counts
- roles and permission bitsets
- bounded recent activity metrics per accessible message channel

## Excluded

- message content
- member names
- member IDs
- bot token

The full message-history index remains in the Discord MCP SQLite layer. Public repository snapshots intentionally contain metadata only.

## Required repository secrets

- `DISCORD_BOT_TOKEN`
- `DISCORD_GUILD_ID`

Never commit either value.
