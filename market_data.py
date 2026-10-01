"""
لایه دریافت داده زنده بازارها
منابع رایگان با چند مسیر جایگزین
"""

import logging
from datetime import datetime
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}
TIMEOUT = 15


def _get(url: str, params: dict = None) -> Optional[Any]:
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            if "json" in ct or r.text.strip().startswith(("{", "[")):
                return r.json()
            return r.text
        logger.warning("HTTP %s %s", r.status_code, url[:80])
        return None
    except Exception as e:
        logger.warning("Request fail %s: %s", url[:60], e)
        return None


def get_crypto() -> dict:
    data = _get(
        "https://api.coingecko.com/api/v3/simple/price",
        {
            "ids": "bitcoin,ethereum,tether,solana,binancecoin",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
    )
    if not data:
        raw = _get("https://api.coinlore.net/api/ticker/?id=90,80,518,48543,2")
        if isinstance(raw, list) and raw:
            mapping = {
                "90": "bitcoin",
                "80": "ethereum",
                "518": "tether",
                "48543": "solana",
                "2": "binancecoin",
            }
            data = {}
            for item in raw:
                mid = str(item.get("id"))
                if mid in mapping:
                    try:
                        data[mapping[mid]] = {
                            "usd": float(item.get("price_usd", 0)),
                            "usd_24h_change": float(item.get("percent_change_24h", 0)),
                        }
                    except Exception:
                        pass

    if not data or not isinstance(data, dict):
        return {"ok": False, "error": "داده کریپتو در دسترس نیست"}

    def fmt(cid, name):
        c = data.get(cid, {})
        if not isinstance(c, dict) or c.get("usd") is None:
            return None
        ch = c.get("usd_24h_change")
        return {
            "name": name,
            "price": float(c["usd"]),
            "change_24h": round(float(ch), 2) if ch is not None else None,
        }

    coins = [
        fmt("bitcoin", "بیت‌کوین (BTC)"),
        fmt("ethereum", "اتریوم (ETH)"),
        fmt("tether", "تتر (USDT)"),
        fmt("solana", "سولانا (SOL)"),
        fmt("binancecoin", "بایننس‌کوین (BNB)"),
    ]
    coins = [c for c in coins if c]
    if not coins:
        return {"ok": False, "error": "داده کریپتو در دسترس نیست"}

    btc_dom = None
    total_mcap = None
    g = _get("https://api.coingecko.com/api/v3/global")
    if isinstance(g, dict) and "data" in g:
        d = g["data"]
        btc_dom = d.get("market_cap_percentage", {}).get("btc")
        total_mcap = d.get("total_market_cap", {}).get("usd")

    return {
        "ok": True,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "coins": coins,
        "btc_dominance": round(btc_dom, 2) if btc_dom else None,
        "total_market_cap_usd": total_mcap,
    }


def get_gold_global() -> dict:
    data = _get("https://api.goldprice.dev/v1/prices", {"symbol": "XAU-USD-SPOT"})
    if isinstance(data, dict) and data.get("symbols"):
        s = data["symbols"][0]
        try:
            return {
                "ok": True,
                "price_usd": float(s.get("price", 0)),
                "bid": s.get("bid"),
                "ask": s.get("ask"),
                "is_stale": bool(s.get("is_stale", False)),
                "updated": s.get("computed_at") or datetime.now().isoformat(),
            }
        except Exception:
            pass
    return {"ok": False, "error": "قیمت انس جهانی در دسترس نیست"}


def get_iran_fx_gold() -> dict:
    result = {"ok": False, "items": [], "updated": datetime.now().strftime("%Y-%m-%d %H:%M")}
    for code, label in [("usd", "دلار آزاد (تقریبی)"), ("eur", "یورو (تقریبی)")]:
        raw = _get(f"https://api.priceto.day/v1/latest/irr/{code}")
        if not isinstance(raw, dict):
            continue
        price = raw.get("price") or raw.get("value") or raw.get("rate")
        if not price and isinstance(raw.get("data"), dict):
            price = raw["data"].get("price") or raw["data"].get("value")
        if price:
            try:
                p = float(str(price).replace(",", ""))
                if p > 50000:
                    p = p / 10
                result["items"].append({"name": label, "price": int(p), "unit": "تومان"})
                result["ok"] = True
            except Exception:
                pass
    if not result["ok"]:
        result["error"] = "داده ارز داخل در حال حاضر در دسترس نیست"
    return result


def get_bourse_index() -> dict:
    result = {
        "ok": False,
        "indices": [],
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "منبع: endpointهای عمومی tsetmc (غیررسمی)",
    }
    for url in [
        "https://cdn.tsetmc.com/api/Index/GetIndexBourse",
        "https://cdn.tsetmc.com/api/Index/GetIndexBourse/0",
    ]:
        data = _get(url)
        if not data:
            continue
        try:
            items = data if isinstance(data, list) else (
                data.get("indexBourse") or data.get("data") or data.get("IndexBourse") or []
            )
            if isinstance(items, dict):
                items = [items]
            for item in (items or [])[:8]:
                if not isinstance(item, dict):
                    continue
                name = item.get("lVal30") or item.get("name") or item.get("indexName") or "شاخص"
                value = item.get("xDrNivJIdx004") or item.get("value") or item.get("indexValue")
                change = item.get("xVarIdxZJlc") or item.get("change") or item.get("changePercent")
                if value is not None:
                    result["indices"].append({"name": str(name), "value": value, "change": change})
            if result["indices"]:
                result["ok"] = True
                break
        except Exception as e:
            logger.warning("bourse parse: %s", e)
    if not result["ok"]:
        result["error"] = "داده شاخص بورس در حال حاضر در دسترس نیست"
    return result


def get_global_markets() -> dict:
    return {
        "ok": True,
        "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "note": "نماینده ریسک‌پذیری: طلا و بیت‌کوین.",
        "gold": get_gold_global(),
        "crypto_summary": get_crypto(),
    }


def format_crypto_message(data: dict) -> str:
    if not data.get("ok"):
        return f"₿ *کریپتو*\n\n⚠️ {data.get('error', 'خطا در دریافت داده')}"
    lines = [f"₿ *وضعیت کریپتو*\n🕐 {data['updated']}\n"]
    for c in data["coins"]:
        ch = c["change_24h"]
        arrow = "🟢" if ch is not None and ch >= 0 else "🔴"
        ch_str = f"{ch:+.2f}%" if ch is not None else "—"
        price = f"{c['price']:,.2f}" if c["price"] < 100 else f"{c['price']:,.0f}"
        lines.append(f"• *{c['name']}*: ${price}  {arrow} {ch_str}")
    if data.get("btc_dominance"):
        lines.append(f"\n📊 دامیننس بیت‌کوین: *{data['btc_dominance']}%*")
    if data.get("total_market_cap_usd"):
        lines.append(f"💰 ارزش کل بازار: *${data['total_market_cap_usd']/1e12:.2f}T*")
    lines.append("\n⚠️ صرفاً اطلاع‌رسانی — سیگنال خرید/فروش نیست.")
    return "\n".join(lines)


def format_gold_message(global_gold: dict, iran_data: dict) -> str:
    lines = ["🥇 *طلا و سکه*\n"]
    if global_gold.get("ok"):
        lines.append(f"🌍 انس جهانی: *${global_gold['price_usd']:,.2f}*")
        lines.append(f"🕐 {str(global_gold.get('updated', ''))[:16]}")
    else:
        lines.append(f"🌍 انس جهانی: ⚠️ {global_gold.get('error', 'در دسترس نیست')}")
    lines.append("")
    if iran_data.get("ok") and iran_data.get("items"):
        lines.append("🇮🇷 داخل (تقریبی):")
        for item in iran_data["items"]:
            lines.append(f"• {item['name']}: *{item['price']:,}* {item.get('unit', '')}")
    else:
        lines.append(f"🇮🇷 داخلی: ⚠️ {iran_data.get('error', 'در دسترس نیست')}")
    lines.append("\n⚠️ برای معامله از منبع معتبر خود استفاده کنید.")
    return "\n".join(lines)


def format_fx_message(iran_data: dict) -> str:
    lines = ["💱 *بازار ارز*\n"]
    if iran_data.get("ok") and iran_data.get("items"):
        lines.append(f"🕐 {iran_data.get('updated', '')}")
        for item in iran_data["items"]:
            lines.append(f"• *{item['name']}*: {item['price']:,} {item.get('unit', 'تومان')}")
    else:
        lines.append(f"⚠️ {iran_data.get('error', 'داده در دسترس نیست')}")
    lines.append("\n⚠️ نرخ‌ها تقریبی‌اند.")
    return "\n".join(lines)


def format_bourse_message(data: dict) -> str:
    lines = ["🇮🇷 *بورس ایران*\n"]
    if data.get("ok") and data.get("indices"):
        lines.append(f"🕐 {data.get('updated', '')}\n")
        for idx in data["indices"]:
            ch = idx.get("change")
            ch_str = f" ({ch})" if ch is not None else ""
            lines.append(f"• *{idx['name']}*: {idx['value']}{ch_str}")
        if data.get("note"):
            lines.append(f"\n_{data['note']}_")
    else:
        lines.append(f"⚠️ {data.get('error', 'داده در دسترس نیست')}")
    lines.append("\n⚠️ منبع غیررسمی. تصمیم‌گیری با tsetmc یا کارگزاری.")
    return "\n".join(lines)


def format_global_message(data: dict) -> str:
    lines = ["🌍 *بازار جهانی*\n", f"🕐 {data.get('updated', '')}\n"]
    gold = data.get("gold") or {}
    if gold.get("ok"):
        lines.append(f"🥇 انس طلا: *${gold['price_usd']:,.2f}*")
    crypto = data.get("crypto_summary")
    if crypto and crypto.get("ok") and crypto.get("coins"):
        btc = next((c for c in crypto["coins"] if "بیت‌کوین" in c["name"]), None)
        if btc:
            ch = btc.get("change_24h")
            if ch is not None:
                arrow = "🟢" if ch >= 0 else "🔴"
                lines.append(f"₿ بیت‌کوین: *${btc['price']:,.0f}* {arrow} {ch:+.2f}%")
            else:
                lines.append(f"₿ بیت‌کوین: *${btc['price']:,.0f}*")
    lines.append(f"\n_{data.get('note', '')}_")
    lines.append("\n⚠️ نمای کلی ریسک‌پذیری بازار.")
    return "\n".join(lines)
