# 🇮🇷 MD Farsi Localization

## MD News — V11 Genesis

بازسازی کامل هستهٔ عملیاتی فارسی‌سازی **Millennium Dawn**.

Genesis از صفر با یک مرزبندی روشن ساخته می‌شود:

- 🧠 **Domain** — قوانین واقعی پروژه و مدل‌های مستقل از Discord
- ⚙️ **Application Services** — منطق ترجمه، مأموریت، بازبینی و دسترسی
- 🗄️ **SQLite** — state عملیاتی و audit history
- 🔌 **Integrations** — ParaTranz و سرویس‌های بیرونی
- 💬 **Discord** — رابط اصلی مدیریت و عملیات
- 🚫 **بدون Dashboard**
- 👥 **Human-in-the-loop** — هیچ ترجمه‌ای خودکار منتشر نمی‌شود

### جریان اصلی

```
Domain
  ↓
Application Services
  ↓
Persistence / Integrations
  ↓
Discord
```

### Translation Intelligence

دستیار ترجمه فقط این کارها را انجام می‌دهد:

1. **Detect** — خطای Placeholder / Variable / Script Tag و ناسازگاری واژه‌نامه
2. **Explain** — توضیح دقیق ایراد
3. **Suggest** — پیشنهاد اصلاح

تصمیم نهایی، بازبینی و انتشار با انسان است.

### منبع حقیقت

- ترجمه و آمار پروژه: **ParaTranz**
- واژه‌نامه رسمی: **ParaTranz Terms**
- state و تاریخچه عملیاتی: **SQLite**

**ParaTranz Project: 19621**

> V10 و Platform Next فعلاً برای حفظ تاریخچه و مقایسه در repository باقی می‌مانند. Genesis مسیر بازسازی جدید است.
