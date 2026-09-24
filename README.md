# 🇮🇷 MD Farsi Localization

## Platform Next — Unified Localization Operations Platform

سامانه یکپارچه فارسی‌سازی **Millennium Dawn**؛ متصل به ParaTranz، Discord و یک Command Center عمومی، با مرزبندی روشن بین اتوماسیون و تصمیم انسانی.

### معماری

~~~text
                       ParaTranz
                           │
                    🐍 Platform Next
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       SQLite           MD news          Dashboard
     history/events    Discord Bot API    public view
          │                │                │
          └────────────────┼────────────────┘
                           │
                    Jobs / Scheduler
              sync • glossary • health • audit
~~~

### نقش زبان‌ها

- 🐍 **Python 3.12+** — Platform Next، orchestration، ParaTranz، analytics، persistence و Discord automation.
- 🦀 **Rust** — validation قطعی و سریع برای tokenهای حساس HOI4/Paradox.
- 🟦 **TypeScript / Node.js** — API gateway فقط‌خواندنی برای deploymentهای نیازمند HTTP API.
- ⚛️ **React + TypeScript + Vite** — داشبورد عمومی و Command Center.
- 🗄️ **SQLite + JSON** — persistence محلی، history و operational snapshots؛ بدون تحمیل سرویس خارجی.
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
**Platform: Next**


### مهاجرت معماری

Platform Next اکنون مسیر عملیاتی canonical پروژه است. مسیرهای قدیمی V9، webhook-based Command Center، workflowهای legacy و اسکریپت‌های مهاجرت‌شده حذف شده‌اند. همه عملیات زمان‌بندی‌شده از `platform/app/cli.py` عبور می‌کنند و Discord فقط از طریق MD news Bot API دریافت‌کننده خروجی است.

اجرای دستی jobها از داخل `platform`:

- `python -m app.cli sync`
- `python -m app.cli report --period daily`
- `python -m app.cli report --period weekly`
- `python -m app.cli glossary-sync`
- `python -m app.cli health`
- `python -m app.cli audit`
