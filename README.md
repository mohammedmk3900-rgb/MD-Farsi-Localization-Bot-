# 🇮🇷 MD Farsi Localization Bot

## 🏛️ Localization Platform V7

Millennium Dawn Farsi Localization is built as a **localization operations platform**, not merely a Discord bot.

### Architecture

```
                  ParaTranz
                      │
                Python Core
                      │
          ┌───────────┼───────────┐
          │           │           │
      Glossary     Analytics    Health
          │           │           │
          └───────────┼───────────┘
                      ↓
               Persistent State
                      ↓
              Read-only JSON API
                      ↓
             TypeScript + React
                Command Center
                      │
                   Discord
                      │
          👥 Management / 💬 Community
          🔎 Human Review Decisions
```

### Language strategy

- **Python 3.12+** — orchestration, ParaTranz integration, persistence, analytics and Discord automation.
- **TypeScript + React** — operator dashboard and interactive visualization.
- **Rust** — reserved for profiled hot paths where native performance or memory safety provides a measurable benefit.

No language is introduced just for novelty. The architecture chooses the simplest tool that satisfies each responsibility.

### Automation boundary

**Automated:** project statistics, progress, deltas, milestones, history, records, health, Discord synchronization, visuals, and ParaTranz Terms synchronization.

**Human-controlled:** management, community moderation, and final translation review/approval decisions.

### Source of truth

**ParaTranz Terms** is the live glossary source of truth. Discord is a presentation/synchronization layer.

### V7 components

- `scripts/command_center/` — Python core
- `dashboard/` — React/TypeScript operator UI
- `rust/` — optional acceleration boundary
- `data/` — versioned persisted state

**ParaTranz project:** `19621`  
**Command Center:** V7
