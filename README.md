# 🇮🇷 MD Farsi Localization

## Command Center V9 — Polyglot Localization Operations Platform

سامانه یکپارچه فارسی‌سازی **Millennium Dawn**؛ متصل به ParaTranz، Discord و یک Command Center عمومی، با مرزبندی روشن بین اتوماسیون و تصمیم انسانی.

### معماری

~~~text
                         ParaTranz
                             │
                      🐍 Python Core
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
      Analytics          Discord Sync       Data Contract
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
            🦀 Rust Engine          ⚛️ React + TS
            token validation         Command Center
                 │                       │
                 └───────────┬───────────┘
                             │
                      🟦 TS API Gateway
                       optional / read-only
~~~

### نقش زبان‌ها

- 🐍 **Python 3.12+** — orchestration، ParaTranz، analytics، persistence و Discord automation.
- 🦀 **Rust** — validation قطعی و سریع برای tokenهای حساس HOI4/Paradox.
- 🟦 **TypeScript / Node.js** — API gateway فقط‌خواندنی برای deploymentهای نیازمند HTTP API.
- ⚛️ **React + TypeScript + Vite** — داشبورد عمومی و Command Center.
- 🗄️ **SQLite + JSON** — persistence محلی و history؛ بدون تحمیل سرویس خارجی.
- ⚙️ **GitHub Actions** — CI، validation و انتشار.

هیچ زبانی صرفاً برای افزایش تعداد زبان‌ها اضافه نشده است.

### مرز اتوماسیون

- 🟢 خودکار: آمار، پیشرفت، تغییرات، تاریخچه، رکوردها، دستاوردها، سلامت، Discord، Terms و انتشار داشبورد.
- 👥 انسانی: مدیریت.
- 💬 انسانی: جامعه و moderation.
- 🔎 انسانی: تصمیم نهایی بازبینی و تأیید/رد ترجمه.

### منبع حقیقت

**ParaTranz** منبع حقیقت داده‌های ترجمه است و **ParaTranz Terms** منبع حقیقت واژه‌نامه رسمی. Discord و Dashboard لایه‌های نمایش و عملیات هستند.

### امنیت

- Secretها فقط در runtimeهای خصوصی CI استفاده می‌شوند.
- public dashboard فقط contract پاک‌سازی‌شده را دریافت می‌کند.
- API عمومی فقط داده‌های public را می‌خواند.
- Rust engine هیچ credential یا webhookی دریافت نمی‌کند.

**ParaTranz Project: 19621**  
**Command Center: V9**
