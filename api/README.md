# 🟦 TypeScript API Gateway V9

A minimal read-only gateway for deployments that need an HTTP API.

Endpoints:

- GET /health
- GET /api/v1/command-center
- GET /api/v1/history

The gateway reads only the public dashboard contract. It has no ParaTranz credentials and never receives Discord webhooks.

GitHub Pages does not require this service; Pages consumes the same generated static JSON directly.
