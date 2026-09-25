# MD News — V11 Genesis

V11 is a clean rebuild of the Millennium Dawn Farsi Localization operations core.

## Principles

- Domain-first: business rules do not depend on Discord, ParaTranz, or HTTP.
- Human-in-the-loop: the assistant detects and suggests; people review and decide.
- ParaTranz Terms is the glossary source of truth.
- SQLite is local operational state and history.
- Discord is the primary operator interface.
- No dashboard.
- No automatic publication of translations.

## Layers

```
Domain
  ↓
Application Services
  ↓
Persistence + Integrations
  ↓
Discord transport
```

V10 remains in repository history while Genesis is built independently.
