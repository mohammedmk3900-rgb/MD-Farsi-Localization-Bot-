# DawnNexus MCP OAuth Setup

DawnNexus uses the MCP OAuth 2.1 resource-server contract for ChatGPT.

## 1. Create an authorization server

Auth0 is the recommended provider for this deployment. OpenAI recommends using an established identity provider rather than implementing an authorization server from scratch.

Create an Auth0 API for DawnNexus:

- Identifier / API audience: choose a stable HTTPS identifier, for example `https://dawnnexus.onrender.com`
- Signing algorithm: RS256
- Add the permission `discord:read`
- Enable RBAC/permissions so the access token contains the granted permission.

For Auth0 MCP support, enable:

- Resource Parameter Compatibility Profile
- CIMD or Dynamic Client Registration, according to the tenant's MCP setup

The Auth0 issuer must be the exact issuer URL, including the trailing slash, for example:

`https://YOUR_TENANT.eu.auth0.com/`

## 2. Configure Render

Set these environment variables on the DawnNexus Render service:

```
MCP_AUTH_MODE=oauth
MCP_RESOURCE_URL=https://dawnnexus.onrender.com
MCP_AUTH_ISSUER=https://YOUR_TENANT.eu.auth0.com/
MCP_AUTH_AUDIENCE=https://dawnnexus.onrender.com
MCP_AUTH_SCOPES=discord:read
```

Optional:

```
MCP_AUTH_JWKS_URL=https://YOUR_TENANT.eu.auth0.com/.well-known/jwks.json
```

Do not put an Auth0 client secret, access token, or other credential in the repository.

The old `MCP_AUTH_TOKEN` is retained only for local/legacy static-bearer deployments. It is not the credential ChatGPT should use for the OAuth connector.

## 3. Verify discovery before creating the ChatGPT app

After Render redeploys, this endpoint must return HTTP 200:

```
GET https://dawnnexus.onrender.com/.well-known/oauth-protected-resource
```

Expected shape:

```json
{
  "resource": "https://dawnnexus.onrender.com",
  "authorization_servers": [
    "https://YOUR_TENANT.eu.auth0.com/"
  ],
  "scopes_supported": ["discord:read"]
}
```

The MCP endpoint remains:

```
https://dawnnexus.onrender.com/mcp
```

An unauthenticated request to `/mcp` should return HTTP 401 with a `WWW-Authenticate` challenge pointing to the protected-resource metadata.

## 4. Create the ChatGPT custom app

In the Custom MCP/App form:

- Name: `DawnNexus`
- Description: `Millennium Dawn Farsi Localization Discord intelligence and project operations MCP.`
- Connection: `MCP Server URL`
- MCP Server URL: `https://dawnnexus.onrender.com/mcp`
- Authentication: `OAuth`

Then use **Scan Tools**.

ChatGPT should discover the protected-resource metadata, follow the Auth0 authorization-server metadata, run OAuth 2.1 Authorization Code + PKCE, and attach the resulting access token to MCP requests.

## 5. Security model

DawnNexus validates:

- JWT signature using the authorization server's JWKS
- RS256 signing algorithm
- issuer
- audience/resource
- expiration and issued-at claims
- required `discord:read` scope/permission

The Discord bot token remains server-side and is never exposed to ChatGPT.

## 6. Important deployment rule

Do not switch Render to `MCP_AUTH_MODE=oauth` until the Auth0 API and MCP authorization configuration are ready. Otherwise DawnNexus will correctly reject MCP calls because no valid OAuth issuer/audience configuration exists.

The static mode remains available for local testing:

```
MCP_AUTH_MODE=static
MCP_AUTH_TOKEN=<32+ character secret>
```
