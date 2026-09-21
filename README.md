# 🇮🇷 MD Farsi Localization

## Command Center V8 — Localization Operations Platform

سامانه یکپارچه فارسی‌سازی **Millennium Dawn**؛ متصل به ParaTranz، Discord و یک داشبورد عمومی سریع و بدون Secret.

### معماری

```
ParaTranz → Python Core V8 → State / History
                 ├→ Discord Automation
                 └→ Public Data Contract → React + TypeScript Dashboard
```

### مرز اتوماسیون

- 🟢 خودکار: آمار، پیشرفت، تغییرات، تاریخچه، رکوردها، دستاوردها، سلامت، Discord، Terms و انتشار داشبورد.
- 👥 انسانی: مدیریت.
- 💬 انسانی: جامعه و moderation.
- 🔎 انسانی: تصمیم نهایی بازبینی و تأیید/رد ترجمه.

### منبع حقیقت

**ParaTranz** منبع حقیقت داده‌های ترجمه است و **ParaTranz Terms** منبع حقیقت واژه‌نامه رسمی. Discord و Dashboard لایه‌های نمایش و عملیات هستند.

### پشته فنی

- Python 3.12+ — Core / collector / analytics / state / Discord
- React 19 + TypeScript + Vite — Command Center
- SQLite + JSON — history و snapshots
- GitHub Actions — automation و deployment
- Rust — فقط در صورت نیاز اثبات‌شده با profiling

### امنیت

داشبورد عمومی فقط داده‌های پاک‌شده و بدون Secret دریافت می‌کند. Token و Webhook وارد payload عمومی نمی‌شوند.

**ParaTranz Project: 19621**  
**Command Center: V8**
