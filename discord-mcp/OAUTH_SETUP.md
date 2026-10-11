# DawnNexus MCP OAuth Setup

DawnNexus currently runs its own OAuth 2.1 authorization server. The runtime does **not** use the Auth0/JWT middleware described by older deployment notes. Keep this guide aligned with the provider implemented in `oauth.py`.

## 1. Configure Render

Set these environment variables on the DawnNexus service:

```dotenv
MCP_PUBLIC_URL=https://dawnnexus.onrender.com
MCP_OAUTH_USERNAME=admin
MCP_OAUTH_PASSWORD=<unique-secret-at-least-16-characters>
MCP_ALLOWED_HOSTS=dawnnexus.onrender.com,dawnnexus.onrender.com:*
MCP_ALLOWED_ORIGINS=https://chatgpt.com,https://chat.openai.com
```

Use a unique password with at least 16 characters. The username defaults to `admin` if `MCP_OAUTH_USERNAME` is omitted. Do not put the password, Discord bot token, OAuth tokens, or database contents in Git.

The Discord bot still needs `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID`. Keep the bot token server-side.

## 2. Verify the deployment

After the service redeploys, open:

- `https://dawnnexus.onrender.com/.well-known/oauth-protected-resource`
- `https://dawnnexus.onrender.com/.well-known/oauth-authorization-server`

The first endpoint should advertise the MCP resource and the authorization server. The second should advertise the built-in OAuth endpoints. The MCP endpoint is:

```
https://dawnnexus.onrender.com/mcp
```

If discovery fails, inspect the Render logs before configuring the ChatGPT connector. The login page should be served at `/oauth/login` when an OAuth authorization request is initiated.

## 3. Connect ChatGPT

In the ChatGPT custom app / MCP connection settings:

- **Name:** DawnNexus
- **Connection:** MCP Server URL
- **MCP Server URL:** `https://dawnnexus.onrender.com/mcp`
- **Authentication:** OAuth

Then scan the available tools and complete the authorization flow. The login screen requests the configured DawnNexus username and password and grants only the `discord:read` scope.

## 4. Security model and limitations

- Access tokens expire after one hour; refresh tokens expire after 30 days.
- Only `discord:read` is granted by the current provider.
- The provider stores client registrations, pending authorization requests, authorization codes, and token records in the configured SQLite database.
- The login password is not stored in SQLite.
- This is a small, single-owner, self-hosted authorization server. It is not Auth0 and should not be described or configured as an Auth0/JWT deployment.
- Discord permissions still limit what the bot can read. A successful MCP connection does not imply access to channels, archived threads, or administrative resources that the bot itself cannot access.

## 5. Troubleshooting

- **Login returns 503:** set `MCP_OAUTH_PASSWORD` to a value of at least 16 characters and redeploy.
- **Login returns 401:** check `MCP_OAUTH_USERNAME` and `MCP_OAUTH_PASSWORD`.
- **ChatGPT cannot discover tools:** verify both OAuth metadata endpoints and `/mcp` are reachable over HTTPS, then inspect Render logs.
- **Missing messages:** run `deep_scan_server` or `sync_server_history`; check the sync cursors and bot permissions. OAuth only authenticates the connector; it does not fill the local message index.
