"""Central Discord webhook renderer/upsert service."""
from __future__ import annotations
from datetime import datetime, timezone
from ..config import Config
from ..http_client import request_json
from ..state import load_json, save_json

MESSAGE_STATE = "data/discord_messages.json"
ICONS = {"healthy": "🟢", "degraded": "🟡", "critical": "🔴"}

def _state() -> dict:
    value = load_json(MESSAGE_STATE, {})
    return value if isinstance(value, dict) else {}

def _write(state: dict) -> None:
    save_json(MESSAGE_STATE, state)

def upsert(webhook: str, key: str, embed: dict) -> str:
    if not webhook:
        raise RuntimeError(f"{key} webhook is not configured.")
    state = _state()
    message_id = str(state.get(key, "")).strip()
    payload = {"username": "MD Farsi Localization • Command Center", "embeds": [embed]}
    if message_id:
        try:
            request_json(f"{webhook}/messages/{message_id}", method="PATCH", payload={"embeds": [embed]})
            return message_id
        except RuntimeError as exc:
            if "HTTP 404" not in str(exc):
                raise
    result = request_json(webhook + "?wait=true", method="POST", payload=payload)
    new_id = str(result.get("id", "")) if isinstance(result, dict) else ""
    if not new_id:
        raise RuntimeError(f"Discord did not return a message ID for {key}.")
    state[key] = new_id
    _write(state)
    return new_id

def stats_embed(config: Config, payload: dict) -> dict:
    stats = payload["stats"]
    progress = payload["progress"]
    now = datetime.now(timezone.utc)
    return {
        "author": {"name": "مرکز فرماندهی فارسی‌سازی Millennium Dawn • نسخه ۹"},
        "title": "📊 آمار و وضعیت پروژه",
        "url": config.project_url,
        "description": f"### 🇮🇷 فارسی‌سازی Millennium Dawn\n**🟢 داده زنده • خودکار • مرجع واحد اطلاعات**\n\n🌐 پیشرفت ترجمه: **{progress['translation_percent']:.2f}%**\n🔎 پیشرفت بازبینی: **{progress['review_percent']:.2f}%**",
        "color": 0x31D7FF,
        "fields": [
            {"name": "📦 پروژه", "value": f"**{stats['files']:,}** فایل\n**{stats['words']:,}** کلمه", "inline": True},
            {"name": "📝 رشته‌ها", "value": f"**{stats['translated']:,}** / **{stats['strings']:,}** ترجمه", "inline": True},
            {"name": "🔎 بازبینی", "value": f"**{stats['reviewed']:,}**\n{progress['review_percent']:.2f}%", "inline": True},
            {"name": "📈 تغییر", "value": f"ترجمه **{progress['delta_translated']:+,}**\nبازبینی **{progress['delta_reviewed']:+,}**", "inline": True},
            {"name": "🎯 باقی‌مانده", "value": f"**{max(0, 100-progress['translation_percent']):.2f}%**", "inline": True},
            {"name": "⚙️ سامانه", "value": "**نسخه ۹ • آنلاین**\nهمگام‌سازی خودکار", "inline": True},
        ],
        "footer": {"text": f"MD Farsi Localization • Sync {now.strftime('%Y-%m-%d %H:%M UTC')}"},
        "timestamp": now.isoformat(),
    }

def progress_embed(config: Config, payload: dict) -> dict:
    progress = payload["progress"]
    now = datetime.now(timezone.utc)
    return {
        "author": {"name": "مرکز فرماندهی فارسی‌سازی Millennium Dawn • نسخه ۹"},
        "title": "📈 پیشرفت زنده پروژه",
        "url": config.project_url,
        "description": f"### 🇮🇷 وضعیت فعلی ترجمه\n\n# **{progress['translation_percent']:.2f}%**\n**{progress['translated']:,}** از **{payload['stats']['strings']:,}** رشته ترجمه شده\n\n🔎 بازبینی: **{progress['review_percent']:.2f}%**",
        "color": 0x35E58A,
        "fields": [
            {"name": "📝 ترجمه‌شده", "value": f"**{progress['translated']:,}**", "inline": True},
            {"name": "🔎 بازبینی‌شده", "value": f"**{progress['reviewed']:,}**", "inline": True},
            {"name": "📄 فایل‌ها", "value": f"**{payload['stats']['files']:,}**", "inline": True},
            {"name": "📈 تغییر اخیر", "value": f"**{progress['delta_translated']:+,}** رشته", "inline": True},
            {"name": "🎯 نقطه عطف", "value": f"{progress['translation_percent']:.2f}%", "inline": True},
            {"name": "⚡ وضعیت", "value": "**آنلاین**", "inline": True},
        ],
        "footer": {"text": f"پروژه ParaTranz ‏{config.project_id} • اتوماسیون نسخه ۹"},
        "timestamp": now.isoformat(),
    }

def health_embed(config: Config, health: dict) -> dict:
    status = health["status"]
    fields = [{"name": key.replace("_", " ").title(), "value": "✅ OK" if value else "❌ FAIL", "inline": True} for key, value in health["checks"].items()]
    return {
        "author": {"name": "مرکز فرماندهی فارسی‌سازی Millennium Dawn • نسخه ۹"},
        "title": "🛰️ سلامت سامانه",
        "description": f"### 🇮🇷 وضعیت عملیاتی سامانه\n\n{ICONS[status]} **{status.upper()}** — **{health['percentage']:.1f}%**\n**{health['passed_checks']}/{health['total_checks']}** بررسی موفق",
        "color": {"healthy": 0x35E58A, "degraded": 0xF1C40F, "critical": 0xE74C3C}[status],
        "fields": fields,
        "footer": {"text": "MD Farsi Localization • موتور سلامت نسخه ۹ • بدون نمایش Secret"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

def achievement_embed(config: Config, threshold: int, payload: dict) -> dict:
    labels = {1: ("🎉", "اولین ۱٪"), 10: ("🌱", "۱۰٪ — آغاز مسیر"), 25: ("📈", "۲۵٪ — یک‌چهارم مسیر"), 50: ("🔥", "۵۰٪ — نیمه مسیر"), 75: ("🚀", "۷۵٪ — نزدیک به تکمیل"), 100: ("🏁", "۱۰۰٪ — تکمیل ترجمه پروژه")}
    icon, label = labels[threshold]
    return {
        "author": {"name": "مرکز فرماندهی فارسی‌سازی Millennium Dawn • نسخه ۹"},
        "title": f"{icon} دستاورد باز شد",
        "url": config.project_url,
        "description": f"### 🇮🇷 فارسی‌سازی Millennium Dawn\n\n## {label}\n🏆 نقطه عطف **{threshold}%** ثبت شد\n📝 **{payload['stats']['translated']:,} / {payload['stats']['strings']:,}** رشته ترجمه شده",
        "color": 0x31D7FF,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
