# 🤼 WWE Bleacher Report Telegram Bot

هر ۳ ساعت یک بار اخبار WWE از Bleacher Report رو با عنوان، تصویر و لینک به تلگرام می‌فرسته.

---

## راه‌اندازی

### ۱. ساخت ربات تلگرام
1. به [@BotFather](https://t.me/BotFather) برو
2. دستور `/newbot` رو بزن و یه اسم انتخاب کن
3. **توکن** رو کپی کن

### ۲. گرفتن Chat ID
- اگه می‌خوای به **خودت** بفرسته: به [@userinfobot](https://t.me/userinfobot) برو و Chat ID خودت رو بگیر
- اگه می‌خوای به **کانال** بفرسته: ربات رو admin کانال کن و Chat ID کانال رو بگیر (مثلاً `@mychannel` یا `-100xxxxxxxxx`)

### ۳. ساخت ریپو GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/wwe-telegram-bot.git
git push -u origin main
```

### ۴. اضافه کردن Secrets به GitHub
برو به **Settings > Secrets and variables > Actions** و دو تا secret اضافه کن:

| نام Secret | مقدار |
|---|---|
| `TELEGRAM_BOT_TOKEN` | توکنی که از BotFather گرفتی |
| `TELEGRAM_CHAT_ID` | Chat ID مقصد |

### ۵. تست
برو به **Actions** و workflow رو دستی اجرا کن (Run workflow).

---

## ساختار فایل‌ها

```
├── bot.py                  # اسکریپت اصلی
├── requirements.txt        # کتابخونه‌ها
├── sent_articles.json      # ذخیره اخبار ارسال شده (auto-generated)
└── .github/
    └── workflows/
        └── wwe_bot.yml     # تنظیمات GitHub Actions
```

---

## نکات

- فایل `sent_articles.json` توسط GitHub Actions cache می‌شه تا اخبار تکراری فرستاده نشه
- اگه ربات نتونست تصویر رو بفرسته، به صورت متن ارسال می‌کنه
- می‌تونی از تب **Actions** هر وقت خواستی دستی اجراش کنی
