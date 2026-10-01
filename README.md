# Investment Intelligence Bot

ربات تلگرام تحلیل سرمایه — مناسب اجرا روی سرور رایگان

## اجرای ۲۴ ساعته روی Render (رایگان)

### مرحله ۱: ساخت حساب
1. برو به: https://render.com
2. با Google یا ایمیل ثبت‌نام کن (رایگان)

### مرحله ۲: ساخت سرویس
1. در داشبورد بزن: **New +**
2. انتخاب کن: **Background Worker**
3. اگر کد روی GitHub است آن را وصل کن
   یا از گزینه **Deploy an existing image from a registry** استفاده نکن
   بهتر: کد را در GitHub بگذار بعد وصل کن

### روش ساده‌تر بدون GitHub (با Railway):
ببین بخش Railway پایین‌تر.

### متغیر محیطی (Environment)
حتماً این را اضافه کن:
- Key: `BOT_TOKEN`
- Value: توکن ربات از BotFather

### Start Command
```
python bot.py
```

### بعد از Deploy
ربات خودکار روشن می‌شود.
در تلگرام `/start` بزن.

---

## اجرای ۲۴ ساعته روی Railway (پیشنهادی و ساده‌تر)

1. برو به: https://railway.app
2. ثبت‌نام با GitHub
3. **New Project** → **Deploy from GitHub repo**
   (اول این پوشه را در یک مخزن GitHub بگذار)
4. یا **Empty Project** بعد **Add Service** → **GitHub Repo**
5. در Variables اضافه کن:
   `BOT_TOKEN` = توکن ربات
6. Deploy

Railway معمولاً برای ربات تلگرام راحت‌تر است.

---

## اجرای محلی (ویندوز)

```bat
set BOT_TOKEN=توکن_خودت
python -m pip install -r requirements.txt
python bot.py
```

---

## امنیت
توکن را هیچ‌وقت در چت عمومی نفرست.
فقط در Environment Variables سایت قرار بده.
