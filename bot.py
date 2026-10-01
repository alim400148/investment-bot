"""
Investment Intelligence Bot - نسخه تلگرام
ربات تحلیل و مدیریت سرمایه چنددارایی

بازارها (هر کدام صفحه جداگانه):
- بورس ایران
- طلا و سکه
- ارز
- کریپتو
- بازار جهانی

قابلیت‌ها:
- وضعیت روزانه هر بازار
- سیگنال خرید (هر تعداد معتبر)
- ورود پله‌ای + حد ضرر
- مدیریت سبد شخصی
- گزارش روزانه
- بدون عدد ساختگی در نبود داده معتبر
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import market_data as md

# ==================== تنظیمات ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

DATA_DIR = Path("user_data")
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==================== مدیریت داده کاربر ====================
def get_user_file(user_id: int) -> Path:
    return DATA_DIR / f"{user_id}.json"


def load_user(user_id: int) -> dict:
    path = get_user_file(user_id)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "capital": None,
        "risk": "متوسط",
        "horizon": "میان‌مدت",
        "portfolio": [],
        "notes": "",
        "created_at": datetime.now().isoformat()
    }


def save_user(user_id: int, data: dict):
    path = get_user_file(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== کیبوردها ====================
def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🇮🇷 بورس ایران"), KeyboardButton("🥇 طلا و سکه")],
            [KeyboardButton("💱 ارز"), KeyboardButton("₿ کریپتو")],
            [KeyboardButton("🌍 بازار جهانی"), KeyboardButton("🎯 همه سیگنال‌ها")],
            [KeyboardButton("💼 سبد من"), KeyboardButton("⚙️ تنظیمات")],
            [KeyboardButton("📅 گزارش روزانه"), KeyboardButton("ℹ️ راهنما")]
        ],
        resize_keyboard=True
    )


def market_keyboard(market_name: str):
    """کیبورد مخصوص هر بازار"""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(f"📊 وضعیت {market_name}"), KeyboardButton(f"🎯 سیگنال {market_name}")],
            [KeyboardButton(f"🔎 تحلیل {market_name}"), KeyboardButton(f"📰 اخبار {market_name}")],
            [KeyboardButton("🔙 بازگشت به منو اصلی")]
        ],
        resize_keyboard=True
    )


# ==================== پیام‌های ثابت ====================
WELCOME = """
🤖 *Investment Intelligence Bot*

دستیار تحلیل و مدیریت سرمایه چنددارایی

*بازارهای پشتیبانی‌شده (هر کدام صفحه جداگانه):*
🇮🇷 بورس ایران
🥇 طلا و سکه
💱 ارز
₿ کریپتو
🌍 بازار جهانی

قابلیت‌ها:
• وضعیت روزانه هر بازار
• سیگنال خرید (هر تعداد معتبر)
• ورود پله‌ای + حد ضرر
• مدیریت سبد شخصی
• گزارش روزانه

⚠️ *توجه مهم:*
این ربات در نبود داده معتبر، عدد ساختگی ارائه نمی‌دهد.
برای سیگنال واقعی باید منابع داده زنده متصل شوند.

از منوی پایین بازار مورد نظر را انتخاب کنید.
"""

HELP_TEXT = """
📖 *راهنمای کامل*

*انتخاب بازار:*
🇮🇷 بورس ایران | 🥇 طلا و سکه | 💱 ارز | ₿ کریپتو | 🌍 بازار جهانی

در هر بازار می‌توانید:
• 📊 وضعیت → خلاصه و چارچوب بررسی
• 🎯 سیگنال → پیشنهادهای خرید معتبر
• 🔎 تحلیل → ساخت پرامپت حرفه‌ای
• 📰 اخبار → محرک‌های مهم

*سایر دستورات:*
💼 سبد من → مدیریت دارایی‌ها
⚙️ تنظیمات → سرمایه / ریسک / افق
📅 گزارش روزانه → جمع‌بندی
🎯 همه سیگنال‌ها → سیگنال‌های همه بازارها

*مثال‌های متنی:*
`سرمایه: 50000000`
`ریسک: متوسط`
`افق: میان‌مدت`
`افزودن دارایی: فولاد - ۱۵ - ارزشی`
`تحلیل: شپنا`
`پاک کردن سبد`
"""

NO_DATA = """
⚠️ *توجه:*
منبع داده زنده هنوز متصل نیست.
به همین دلیل عدد قیمت یا سیگنال ساختگی ارائه نمی‌شود.

فعلاً فقط *چارچوب تحلیل و ساختار حرفه‌ای* در اختیار شماست.
پس از اتصال API، سیگنال‌های واقعی فعال می‌شوند.
"""


# ==================== محتوای هر بازار ====================
MARKETS = {
    "بورس ایران": {
        "emoji": "🇮🇷",
        "status": """
🇮🇷 *وضعیت روزانه — بورس ایران*
تاریخ: {date}

{no_data}

---
*چارچوب بررسی روزانه بورس:*

🔹 *شاخص‌ها*
• شاخص کل و هم‌وزن
• ارزش و حجم معاملات
• تعداد نمادهای مثبت / منفی

🔹 *صنایع*
• صنایع پیشرو امروز
• صنایع عقب‌مانده
• ورود و خروج پول هوشمند

🔹 *نمادهای مهم*
• نمادهای با حجم غیرعادی
• صف‌های خرید و فروش سنگین
• گزارش‌های مهم شرکتی

🔹 *عوامل کلان*
• نرخ بهره و اوراق
• اخبار بودجه و سیاست‌های اقتصادی
• تأثیر دلار و طلا بر بورس
""",
        "signals": """
🎯 *سیگنال‌های خرید — بورس ایران*

سرمایه شما: *{capital}*
ریسک: *{risk}*

{no_data}

---
*قوانین سیگنال بورس:*

✅ فقط در صورت وجود شرایط زیر سیگنال داده می‌شود:
• روند شاخص و صنعت همسو باشد
• نسبت ریسک به ریوارد حداقل ۱:۲
• نقطه ورود + حد ضرر مشخص
• اندازه موقعیت متناسب با سرمایه و ریسک شما
• نقدشوندگی مناسب نماد

❌ در نبود داده معتبر → هیچ سیگنالی ساخته نمی‌شود.

*ورود پله‌ای پیشنهادی (پس از فعال‌سازی داده):*
• پله اول: ۴۰٪ موقعیت
• پله دوم: ۳۰٪ (در صورت تأیید)
• پله سوم: ۳۰٪ (در صورت ادامه روند)
""",
        "news": """
📰 *اخبار و محرک‌های مهم — بورس ایران*

{no_data}

*د دسته‌بندی محرک‌ها:*
• گزارش‌های ماهانه و فصلی شرکت‌ها
• تصمیمات سازمان بورس
• اخبار کلان اقتصادی و بودجه
• تغییرات نرخ بهره و اوراق
• اخبار صنایع خاص (پتروشیمی، فلزات، بانک و ...)
""",
        "analyze_hint": "نام نماد بورسی را بفرستید (مثال: تحلیل: فولاد یا تحلیل: شپنا)"
    },
    "طلا و سکه": {
        "emoji": "🥇",
        "status": """
🥇 *وضعیت روزانه — طلا و سکه*
تاریخ: {date}

{no_data}

---
*چارچوب بررسی روزانه طلا:*

🔹 *قیمت جهانی*
• انس جهانی طلا
• تغییرات روزانه و هفتگی
• همبستگی با دلار جهانی و بازدهی اوراق

🔹 *بازار داخل*
• قیمت سکه طرح جدید / امامی
• حباب سکه
• نسبت دلار آزاد به طلا

🔹 *عوامل تأثیرگذار*
• سیاست‌های فدرال رزرو
• تنش‌های ژئوپلیتیک
• تقاضای فیزیکی داخل و جهانی
""",
        "signals": """
🎯 *سیگنال‌های خرید — طلا و سکه*

سرمایه شما: *{capital}*
ریسک: *{risk}*

{no_data}

---
*قوانین سیگنال طلا:*

✅ شرایط لازم برای سیگنال:
• همسویی روند جهانی و داخلی
• حباب سکه در محدوده منطقی
• نسبت ریسک به ریوارد مناسب
• نقطه ورود و حد ضرر مشخص

*انواع موقعیت:*
• سکه فیزیکی / بانکی
• طلای آب‌شده
• صندوق‌های طلا (در صورت فعال بودن)
""",
        "news": """
📰 *اخبار و محرک‌های مهم — طلا و سکه*

{no_data}

*محرک‌های کلیدی:*
• تصمیمات فدرال رزرو و نرخ بهره آمریکا
• داده‌های تورم جهانی
• تنش‌های سیاسی و نظامی
• تقاضای بانک‌های مرکزی
• اخبار داخلی مربوط به سکه و طلا
""",
        "analyze_hint": "نوع طلا را مشخص کنید (مثال: تحلیل: سکه امامی یا تحلیل: انس جهانی)"
    },
    "ارز": {
        "emoji": "💱",
        "status": """
💱 *وضعیت روزانه — بازار ارز*
تاریخ: {date}

{no_data}

---
*چارچوب بررسی روزانه ارز:*

🔹 *نرخ‌های کلیدی*
• دلار آزاد
• دلار نیما / توافقی
• یورو و سایر ارزهای مهم
• شکاف نرخ‌ها

🔹 *عوامل تأثیرگذار*
• عرضه و تقاضای اسکناس
• سیاست‌های بانک مرکزی
• اخبار مذاکرات و تحریم‌ها
• تراز تجاری و درآمدهای نفتی
""",
        "signals": """
🎯 *سیگنال‌های خرید — ارز*

سرمایه شما: *{capital}*
ریسک: *{risk}*

{no_data}

---
*قوانین سیگنال ارز:*

⚠️ بازار ارز بسیار حساس و پرریسک است.
سیگنال فقط در صورت وجود شرایط بسیار قوی و داده معتبر ارائه می‌شود.

• نقطه ورود و حد ضرر الزامی
• اندازه موقعیت محافظه‌کارانه
• توجه به ریسک‌های ناگهانی خبری
""",
        "news": """
📰 *اخبار و محرک‌های مهم — ارز*

{no_data}

*محرک‌های اصلی:*
• تصمیمات و سیاست‌های بانک مرکزی
• اخبار مذاکرات و روابط خارجی
• عرضه ارز در سامانه نیما
• تحولات منطقه‌ای و جهانی
""",
        "analyze_hint": "نوع ارز را مشخص کنید (مثال: تحلیل: دلار آزاد یا تحلیل: یورو)"
    },
    "کریپتو": {
        "emoji": "₿",
        "status": """
₿ *وضعیت روزانه — کریپتو*
تاریخ: {date}

{no_data}

---
*چارچوب بررسی روزانه کریپتو:*

🔹 *بازار کلی*
• بیت‌کوین و اتریوم
• دامیننس بیت‌کوین
• شاخص ترس و طمع
• حجم معاملات کل بازار

🔹 *آلت‌کوین‌ها*
• عملکرد بخش‌های مختلف (DeFi، Layer2، AI و ...)
• کوین‌های با حجم و مومنتوم بالا

🔹 *عوامل کلان*
• همبستگی با بازار سهام آمریکا
• اخبار رگولاتوری
• جریان ورودی/خروجی صندوق‌های ETF
""",
        "signals": """
🎯 *سیگنال‌های خرید — کریپتو*

سرمایه شما: *{capital}*
ریسک: *{risk}*

{no_data}

---
*قوانین سیگنال کریپتو:*

✅ شرایط لازم:
• روند بیت‌کوین همسو باشد (یا حداقل خنثی نباشد)
• نسبت ریسک به ریوارد حداقل ۱:۲
• حجم معاملات کافی
• نقطه ورود + حد ضرر واضح
• اندازه موقعیت متناسب با نوسان بالای این بازار

*ورود پله‌ای:*
• پله ۱: ۴۰٪
• پله ۲: ۳۰٪
• پله ۳: ۳۰٪
""",
        "news": """
📰 *اخبار و محرک‌های مهم — کریپتو*

{no_data}

*محرک‌های کلیدی:*
• تصمیمات SEC و رگولاتوری آمریکا
• جریان ورودی/خروجی ETFهای بیت‌کوین و اتریوم
• آپگریدهای مهم شبکه‌ها
• اخبار کلان اقتصادی مؤثر بر ریسک‌پذیری
""",
        "analyze_hint": "نام رمزارز را بفرستید (مثال: تحلیل: بیت‌کوین یا تحلیل: اتریوم)"
    },
    "بازار جهانی": {
        "emoji": "🌍",
        "status": """
🌍 *وضعیت روزانه — بازار جهانی*
تاریخ: {date}

{no_data}

---
*چارچوب بررسی روزانه:*

🔹 *شاخص‌های سهام*
• S&P 500 ، Nasdaq ، Dow Jones
• شاخص‌های اروپایی و آسیایی

🔹 *کالاها*
• نفت خام (برنت و WTI)
• مس و سایر فلزات صنعتی

🔹 *نرخ بهره و اوراق*
• بازدهی اوراق ۱۰ ساله آمریکا
• انتظارات نرخ بهره فدرال رزرو

🔹 *تأثیر بر بازار ایران*
• تأثیر دلار جهانی و نفت بر بورس و ارز داخل
""",
        "signals": """
🎯 *سیگنال‌های خرید — بازار جهانی*

سرمایه شما: *{capital}*
ریسک: *{risk}*

{no_data}

---
این بخش بیشتر برای رصد تأثیر بازارهای جهانی بر دارایی‌های داخلی است.
سیگنال مستقیم روی ابزارهای جهانی فقط در صورت دسترسی و داده معتبر ارائه می‌شود.
""",
        "news": """
📰 *اخبار و محرک‌های مهم — بازار جهانی*

{no_data}

*محرک‌های کلیدی:*
• تصمیمات فدرال رزرو و بانک‌های مرکزی بزرگ
• داده‌های اشتغال و تورم آمریکا
• تنش‌های ژئوپلیتیک
• قیمت نفت و کالاهای اساسی
""",
        "analyze_hint": "موضوع مورد نظر را بفرستید (مثال: تحلیل: نفت برنت یا تحلیل: S&P 500)"
    }
}


# ==================== توابع کمکی ====================
def format_capital(user_data: dict) -> str:
    capital = user_data.get("capital")
    return f"{capital:,} تومان" if capital else "تنظیم نشده"


def get_market_from_text(text: str) -> str | None:
    mapping = {
        "بورس ایران": "بورس ایران",
        "طلا و سکه": "طلا و سکه",
        "طلا": "طلا و سکه",
        "ارز": "ارز",
        "کریپتو": "کریپتو",
        "بازار جهانی": "بازار جهانی",
        "جهانی": "بازار جهانی",
    }
    for key, val in mapping.items():
        if key in text:
            return val
    return None


# ==================== هندلرها ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    load_user(update.effective_user.id)
    context.user_data["current_market"] = None
    await update.message.reply_text(WELCOME, parse_mode="Markdown", reply_markup=main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown", reply_markup=main_keyboard())


async def show_market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, market: str):
    context.user_data["current_market"] = market
    emoji = MARKETS[market]["emoji"]
    text = f"{emoji} *صفحه {market}*\n\nیکی از گزینه‌های زیر را انتخاب کنید:"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=market_keyboard(market))


async def market_status(update: Update, context: ContextTypes.DEFAULT_TYPE, market: str):
    """نمایش وضعیت زنده هر بازار"""
    await update.message.reply_text("⏳ در حال دریافت داده زنده...", reply_markup=market_keyboard(market))

    if market == "کریپتو":
        data = md.get_crypto()
        text = md.format_crypto_message(data)
    elif market == "طلا و سکه":
        g = md.get_gold_global()
        i = md.get_iran_fx_gold()
        text = md.format_gold_message(g, i)
    elif market == "ارز":
        i = md.get_iran_fx_gold()
        text = md.format_fx_message(i)
    elif market == "بورس ایران":
        data = md.get_bourse_index()
        text = md.format_bourse_message(data)
    elif market == "بازار جهانی":
        data = md.get_global_markets()
        text = md.format_global_message(data)
    else:
        data = MARKETS.get(market, {})
        text = data.get("status", "بازار نامعتبر").format(
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            no_data=NO_DATA
        )

    # اگر داده زنده نبود، چارچوب قبلی را هم نشان بده
    if "⚠️" in text and "در دسترس نیست" in text:
        framework = MARKETS.get(market, {}).get("status", "")
        if framework:
            extra = framework.format(
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                no_data=""
            )
            text += "\n\n---\n*چارچوب بررسی:*\n" + extra[:800]

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=market_keyboard(market))


async def market_signals(update: Update, context: ContextTypes.DEFAULT_TYPE, market: str):
    user_data = load_user(update.effective_user.id)
    data = MARKETS[market]
    text = data["signals"].format(
        capital=format_capital(user_data),
        risk=user_data.get("risk", "متوسط"),
        no_data=NO_DATA
    )

    # اضافه کردن خلاصه داده زنده (بدون ساخت سیگنال جعلی)
    live_note = ""
    try:
        if market == "کریپتو":
            c = md.get_crypto()
            if c.get("ok") and c.get("coins"):
                live_note = "\n\n📡 *داده زنده موجود:*\n"
                for coin in c["coins"][:3]:
                    ch = coin.get("change_24h")
                    ch_s = f"{ch:+.2f}%" if ch is not None else "—"
                    live_note += f"• {coin['name']}: ${coin['price']:,.0f} ({ch_s})\n"
                live_note += "\n_سیگنال خرید خودکار صادر نمی‌شود. فقط داده نمایش داده می‌شود._"
        elif market == "طلا و سکه":
            g = md.get_gold_global()
            if g.get("ok"):
                live_note = f"\n\n📡 انس جهانی زنده: *${g['price_usd']:,.2f}*\n_سیگنال خودکار صادر نمی‌شود._"
        elif market == "بورس ایران":
            b = md.get_bourse_index()
            if b.get("ok") and b.get("indices"):
                live_note = "\n\n📡 *شاخص‌های در دسترس:*\n"
                for idx in b["indices"][:3]:
                    live_note += f"• {idx['name']}: {idx['value']}\n"
                live_note += "\n_سیگنال خودکار روی نماد صادر نمی‌شود._"
    except Exception:
        pass

    text = text + live_note
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=market_keyboard(market))


async def market_news(update: Update, context: ContextTypes.DEFAULT_TYPE, market: str):
    data = MARKETS[market]
    text = data["news"].format(no_data=NO_DATA)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=market_keyboard(market))


async def market_analyze_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, market: str):
    hint = MARKETS[market]["analyze_hint"]
    context.user_data["waiting_analyze_market"] = market
    text = f"🔎 *تحلیل در بازار {market}*\n\n{hint}"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=market_keyboard(market))


async def all_signals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = load_user(update.effective_user.id)
    await update.message.reply_text("⏳ در حال جمع‌آوری داده از همه بازارها...")

    parts = [
        f"🎯 *خلاصه داده زنده همه بازارها*",
        f"سرمایه: *{format_capital(user_data)}* | ریسک: *{user_data.get('risk', 'متوسط')}*",
        f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "⚠️ *سیگنال خرید خودکار صادر نمی‌شود.* فقط داده خام نمایش داده می‌شود.",
        "---"
    ]

    try:
        c = md.get_crypto()
        if c.get("ok"):
            parts.append("₿ *کریپتو*")
            for coin in c.get("coins", [])[:3]:
                ch = coin.get("change_24h")
                ch_s = f"{ch:+.2f}%" if ch is not None else "—"
                parts.append(f"  • {coin['name']}: ${coin['price']:,.0f} ({ch_s})")
        else:
            parts.append("₿ کریپتو: داده در دسترس نیست")
    except Exception:
        parts.append("₿ کریپتو: خطا")

    try:
        g = md.get_gold_global()
        if g.get("ok"):
            parts.append(f"\n🥇 انس طلا: *${g['price_usd']:,.2f}*")
        else:
            parts.append("\n🥇 طلا: داده در دسترس نیست")
    except Exception:
        parts.append("\n🥇 طلا: خطا")

    try:
        b = md.get_bourse_index()
        if b.get("ok") and b.get("indices"):
            parts.append("\n🇮🇷 *بورس*")
            for idx in b["indices"][:2]:
                parts.append(f"  • {idx['name']}: {idx['value']}")
        else:
            parts.append("\n🇮🇷 بورس: داده در دسترس نیست")
    except Exception:
        parts.append("\n🇮🇷 بورس: خطا")

    try:
        fx = md.get_iran_fx_gold()
        if fx.get("ok") and fx.get("items"):
            parts.append("\n💱 *ارز*")
            for item in fx["items"][:2]:
                parts.append(f"  • {item['name']}: {item['price']:,}")
        else:
            parts.append("\n💱 ارز: داده در دسترس نیست")
    except Exception:
        parts.append("\n💱 ارز: خطا")

    parts.append("\n---\nبرای جزئیات بیشتر وارد صفحه هر بازار شوید.")
    text = "\n".join(parts)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = load_user(update.effective_user.id)
    portfolio = user_data.get("portfolio", [])

    if not portfolio:
        text = """
💼 *سبد شخصی شما*

هنوز هیچ دارایی ثبت نشده.

برای افزودن:
`افزودن دارایی: نام - وزن٪ - نقش`

مثال‌ها:
`افزودن دارایی: فولاد - ۱۵ - ارزشی`
`افزودن دارایی: بیت‌کوین - ۲۵ - رشدی`
`افزودن دارایی: سکه - ۲۰ - حفظ ارزش`
"""
    else:
        lines = []
        total = 0
        for i, item in enumerate(portfolio, 1):
            lines.append(f"{i}. *{item['name']}* | {item['weight']}% | {item['role']}")
            try:
                total += float(item.get("weight", 0))
            except Exception:
                pass
        text = f"""
💼 *سبد شخصی شما*

سرمایه: *{format_capital(user_data)}*
تعداد: *{len(portfolio)}* | مجموع وزن: *{total}%*

{chr(10).join(lines)}

---
افزودن: `افزودن دارایی: نام - وزن - نقش`
پاک کردن همه: `پاک کردن سبد`
"""
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = load_user(update.effective_user.id)
    text = f"""
⚙️ *تنظیمات شما*

💰 سرمایه: *{format_capital(user_data)}*
⚖️ ریسک: *{user_data.get('risk', 'متوسط')}*
📅 افق: *{user_data.get('horizon', 'میان‌مدت')}*

---
تغییر با این دستورات:
`سرمایه: 50000000`
`ریسک: کم` یا `متوسط` یا `زیاد`
`افق: کوتاه‌مدت` یا `میان‌مدت` یا `بلندمدت`
"""
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


async def daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = load_user(update.effective_user.id)
    text = f"""
📅 *گزارش روزانه*
{datetime.now().strftime('%Y-%m-%d %H:%M')}

👤 سرمایه: *{format_capital(user_data)}*
⚖️ ریسک: *{user_data.get('risk', 'متوسط')}*
📊 تعداد دارایی در سبد: *{len(user_data.get('portfolio', []))}*

{NO_DATA}

---
*چک‌لیست روزانه:*
۱. بررسی وضعیت هر بازار (از منوی اصلی)
۲. چک اخبار و محرک‌ها
۳. مرور سبد و وزن‌ها
۴. فقط در صورت سیگنال معتبر → اقدام
"""
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_keyboard())


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    user_data = load_user(user_id)
    current_market = context.user_data.get("current_market")

    # بازگشت به منو اصلی
    if text == "🔙 بازگشت به منو اصلی":
        context.user_data["current_market"] = None
        await update.message.reply_text("منوی اصلی:", reply_markup=main_keyboard())
        return

    # ورود به صفحات بازار
    if text in ["🇮🇷 بورس ایران", "بورس ایران"]:
        await show_market_menu(update, context, "بورس ایران")
        return
    if text in ["🥇 طلا و سکه", "طلا و سکه"]:
        await show_market_menu(update, context, "طلا و سکه")
        return
    if text in ["💱 ارز", "ارز"]:
        await show_market_menu(update, context, "ارز")
        return
    if text in ["₿ کریپتو", "کریپتو"]:
        await show_market_menu(update, context, "کریپتو")
        return
    if text in ["🌍 بازار جهانی", "بازار جهانی"]:
        await show_market_menu(update, context, "بازار جهانی")
        return

    # دکمه‌های داخل هر بازار
    if current_market:
        if text.startswith("📊 وضعیت"):
            await market_status(update, context, current_market)
            return
        if text.startswith("🎯 سیگنال"):
            await market_signals(update, context, current_market)
            return
        if text.startswith("📰 اخبار"):
            await market_news(update, context, current_market)
            return
        if text.startswith("🔎 تحلیل"):
            await market_analyze_prompt(update, context, current_market)
            return

    # دکمه‌های منوی اصلی
    if text == "🎯 همه سیگنال‌ها":
        await all_signals(update, context)
        return
    if text == "💼 سبد من":
        await portfolio(update, context)
        return
    if text == "⚙️ تنظیمات":
        await settings(update, context)
        return
    if text == "📅 گزارش روزانه":
        await daily_report(update, context)
        return
    if text == "ℹ️ راهنما":
        await help_command(update, context)
        return

    # تنظیمات متنی
    if text.startswith("سرمایه:") or text.startswith("سرمایه "):
        try:
            value = text.replace("سرمایه:", "").replace("سرمایه", "").strip().replace(",", "")
            capital = int(value)
            user_data["capital"] = capital
            save_user(user_id, user_data)
            await update.message.reply_text(f"✅ سرمایه روی *{capital:,} تومان* تنظیم شد.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ مثال درست: `سرمایه: 50000000`", parse_mode="Markdown")
        return

    if text.startswith("ریسک:") or text.startswith("ریسک "):
        risk = text.replace("ریسک:", "").replace("ریسک", "").strip()
        if risk in ["کم", "متوسط", "زیاد"]:
            user_data["risk"] = risk
            save_user(user_id, user_data)
            await update.message.reply_text(f"✅ ریسک روی *{risk}* تنظیم شد.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ فقط: کم / متوسط / زیاد")
        return

    if text.startswith("افق:") or text.startswith("افق "):
        horizon = text.replace("افق:", "").replace("افق", "").strip()
        if horizon in ["کوتاه‌مدت", "میان‌مدت", "بلندمدت"]:
            user_data["horizon"] = horizon
            save_user(user_id, user_data)
            await update.message.reply_text(f"✅ افق روی *{horizon}* تنظیم شد.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ فقط: کوتاه‌مدت / میان‌مدت / بلندمدت")
        return

    if text.startswith("افزودن دارایی:"):
        try:
            parts = text.replace("افزودن دارایی:", "").strip().split("-")
            if len(parts) >= 3:
                name = parts[0].strip()
                weight = parts[1].strip().replace("%", "")
                role = parts[2].strip()
                user_data["portfolio"].append({"name": name, "weight": weight, "role": role})
                save_user(user_id, user_data)
                await update.message.reply_text(f"✅ *{name}* با وزن {weight}% اضافه شد.", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ فرمت: `افزودن دارایی: نام - وزن - نقش`", parse_mode="Markdown")
        except Exception:
            await update.message.reply_text("❌ خطا در افزودن دارایی.")
        return

    if text == "پاک کردن سبد":
        user_data["portfolio"] = []
        save_user(user_id, user_data)
        await update.message.reply_text("✅ سبد پاک شد.")
        return

    # تحلیل دارایی
    if text.startswith("تحلیل:") or text.startswith("تحلیل "):
        asset = text.replace("تحلیل:", "").replace("تحلیل", "").strip()
        if not asset:
            await update.message.reply_text("نام دارایی را بنویسید.")
            return

        market = context.user_data.get("waiting_analyze_market") or context.user_data.get("current_market") or "عمومی"
        capital = format_capital(user_data)
        risk = user_data.get("risk", "متوسط")
        horizon = user_data.get("horizon", "میان‌مدت")

        prompt = f"""
🧠 *پرامپت تحلیل آماده*

بازار: *{market}*
دارایی: *{asset}*

---
شما یک تحلیل‌گر حرفه‌ای بازارهای مالی هستید.
تحلیل کامل «{asset}» را برای سرمایه‌گذار با این مشخصات انجام دهید:

• سرمایه قابل استفاده: {capital}
• سطح ریسک: {risk}
• افق زمانی: {horizon}
• بازار مربوطه: {market}

موارد الزامی در پاسخ:
۱. خلاصه اجرایی (۳–۵ خط)
۲. داده‌های کلیدی به‌روز (اگر در اختیار دارید)
۳. تحلیل تکنیکال و بنیادی مختصر
۴. سناریوهای صعودی / خنثی / نزولی
۵. نسبت ریسک به ریوارد پیشنهادی
۶. نقطه ورود (در صورت مناسب بودن)
۷. حد ضرر (نقطه ابطال)
۸. اندازه موقعیت پیشنهادی نسبت به سرمایه
۹. شرایطی که خرید نباید انجام شود

⚠️ اگر داده معتبر و به‌روز ندارید، صریحاً اعلام کنید و عدد ساختگی ندهید.
---
این متن را کپی کرده و در ChatGPT یا مدل هوش مصنوعی قرار دهید.
"""
        await update.message.reply_text(prompt, parse_mode="Markdown")
        context.user_data.pop("waiting_analyze_market", None)
        return

    # پیام پیش‌فرض
    await update.message.reply_text(
        "دستور را متوجه نشدم.\nاز منوی پایین استفاده کنید یا /help بزنید.",
        reply_markup=main_keyboard()
    )


def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or not BOT_TOKEN:
        print("=" * 50)
        print("❌ توکن ربات تنظیم نشده!")
        print("توکن را از @BotFather بگیرید و این دستور را بزنید:")
        print("export BOT_TOKEN='توکن_شما'")
        print("یا در ویندوز: $env:BOT_TOKEN='توکن_شما'")
        print("=" * 50)
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ ربات Investment Intelligence (نسخه چندبازاری) در حال اجراست...")
    print("بازارها: بورس ایران | طلا | ارز | کریپتو | بازار جهانی")
    print("برای توقف: Ctrl+C")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
