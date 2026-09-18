# Discord MCP — Read-Only Bridge

A small, read-only Model Context Protocol (MCP) server for the Millennium Dawn Farsi Localization Discord server.

## Architecture

Discord Server → Discord Bot (read-only) → Remote MCP Server → ChatGPT Custom App

The server exposes only read operations:

- `get_server_overview`
- `list_channels`
- `list_roles`
- `read_channel`
- `search_messages`

No Discord messages, roles, channels, or permissions are modified by this project.

## Requirements

- Python 3.11+
- A Discord bot token
- The Discord server (guild) ID
- A host that can expose the MCP endpoint over HTTPS

## Configuration

Copy `.env.example` to `.env`:

```env
DISCORD_BOT_TOKEN=replace_me
DISCORD_GUILD_ID=replace_me
MCP_HOST=0.0.0.0
MCP_PORT=8000
```

Never commit a real token.

For the Discord bot, grant only the permissions needed to view the target channels and read message history. Keep the bot read-only.

## Run locally

```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python server.py
```

The Streamable HTTP MCP endpoint is served by the FastMCP server.

## Docker

```bash
docker build -t md-discord-mcp .
docker run --rm -p 8000:8000 --env-file .env md-discord-mcp
```

Put the service behind HTTPS before connecting it to ChatGPT.

## Security

This bridge deliberately starts with read-only capabilities. Do not add message sending, moderation, role management, or other write tools until there is a separate permission model and explicit authorization flow.

The bot token must be supplied as a deployment secret/environment variable, never in source control.
