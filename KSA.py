import requests
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime
import time
import schedule

# ── إعدادات ──────────────────────────────────────────
TELEGRAM_TOKEN = "8784816733:AAF2FpH9EqJ85BzVUjSXH1UI4McDIhSbNvI"
CHAT_ID        = "1621604072"

# ── أكبر 30 سهم في تداول ─────────────────────────────
# الرمز في Yahoo Finance للسوق السعودي ينتهي بـ .SR
TADAWUL30 = [
    "2222.SR",  # أرامكو
    "1180.SR",  # الأهلي
    "1120.SR",  # الراجحي
    "2010.SR",  # سابك
    "2350.SR",  # المملكة القابضة
    "7010.SR",  # الاتصالات السعودية
    "7020.SR",  # موبايلي
    "7030.SR",  # زين السعودية
    "2330.SR",  # أدفانسد
    "4200.SR",  # بنك البلاد
    "1010.SR",  # الرياض
    "1050.SR",  # بنك السعودي الفرنسي
    "1060.SR",  # البنك السعودي للاستثمار
    "1080.SR",  # Arab National Bank
    "1150.SR",  # بنك الجزيرة
    "2001.SR",  # المتقدمة للبتروكيماويات
    "2020.SR",  # سبكيم
    "2060.SR",  # إيثيلين
    "2290.SR",  # أبوقير للأسمدة
    "2380.SR",  # بترو رابغ
    "3010.SR",  # سيمنس العربية
    "3030.SR",  # بوان
    "3160.SR",  # المراعي
    "4001.SR",  # التأمين العربي
    "4030.SR",  # ميدغلف
    "4050.SR",  # المتحدة للتأمين
    "4161.SR",  # تكافل الراجحي
    "4240.SR",  # بوبا العربية
    "6010.SR",  # سابتا
    "8010.SR",  # معادن
]

# ── إرسال تيليجرام ───────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot8784816733:AAF2FpH9EqJ85BzVUjSXH1UI4McDIhSbNvI/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"خطأ إرسال تيليجرام: {e}")

# ── أسماء الشركات بالعربي ────────────────────────────
NAMES = {
    "2222.SR": "أرامكو",
    "1180.SR": "الأهلي",
    "1120.SR": "الراجحي",
    "2010.SR": "سابك",
    "2350.SR": "المملكة القابضة",
    "7010.SR": "الاتصالات السعودية",
    "7020.SR": "موبايلي",
    "7030.SR": "زين السعودية",
    "2330.SR": "أدفانسد",
    "4200.SR": "بنك البلاد",
    "1010.SR": "الرياض",
    "1050.SR": "السعودي الفرنسي",
    "1060.SR": "السعودي للاستثمار",
    "1080.SR": "Arab National Bank",
    "1150.SR": "الجزيرة",
    "2001.SR": "المتقدمة",
    "2020.SR": "سبكيم",
    "2060.SR": "إيثيلين",
    "2290.SR": "أبوقير",
    "2380.SR": "بترو رابغ",
    "3010.SR": "سيمنس العربية",
    "3030.SR": "بوان",
    "3160.SR": "المراعي",
    "4001.SR": "التأمين العربي",
    "4030.SR": "ميدغلف",
    "4050.SR": "المتحدة للتأمين",
    "4161.SR": "تكافل الراجحي",
    "4240.SR": "بوبا العربية",
    "6010.SR": "سابتا",
    "8010.SR": "معادن",
}

# ── تحليل سهم واحد ───────────────────────────────────
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None

        # ── المؤشرات ──────────────────────────────────
        df["EMA10"]  = ta.ema(df["Close"], length=10)
        df["EMA20"]  = ta.ema(df["Close"], length=20)
        df["EMA50"]  = ta.ema(df["Close"], length=50)
        df["EMA200"] = ta.ema(df["Close"], length=200)
        df["RSI"]    = ta.rsi(df["Close"], length=14)

        macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        df["MACD"]        = macd["MACD_12_26_9"]
        df["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price    = round(float(last["Close"]), 2)
        rsi      = round(float(last["RSI"]), 1)
        ema10    = round(float(last["EMA10"]), 2)
        ema20    = round(float(last["EMA20"]), 2)
        ema50    = round(float(last["EMA50"]), 2)
        ema200   = round(float(last["EMA200"]), 2)
        macd_val = round(float(last["MACD"]), 4)
        macd_sig = round(float(last["MACD_SIGNAL"]), 4)

        prev_close = round(float(prev["Close"]), 2)
        change_pct = round(((price - prev_close) / prev_close) * 100, 2)

        # تقاطع EMA10 فوق EMA20
        ema10_cross = (
            float(prev["EMA10"]) < float(prev["EMA20"]) and
            float(last["EMA10"]) > float(last["EMA20"])
        )

        # ── الإشارات ──────────────────────────────────
        signals    = []
        buy_score  = 0
        sell_score = 0

        # RSI
        if rsi < 40:
            signals.append("🔵 RSI تشبع بيع")
            buy_score += 1
        elif rsi > 65:
            signals.append("🔴 RSI تشبع شراء")
            sell_score += 1
        else:
            signals.append(f"⚪ RSI محايد {rsi}")

        # تقاطع EMA10/EMA20
        if ema10_cross:
            signals.append("⭐ تقاطع EMA10 فوق EMA20")
            buy_score += 2

        # EMA الاتجاه
        if price > ema10 > ema20 > ema50 > ema200:
            signals.append("🟢 فوق EMA10/20/50/200 — صاعد قوي")
            buy_score += 2
        elif price > ema20 > ema50:
            signals.append("🟢 فوق EMA20/50 — صاعد")
            buy_score += 1
        elif price < ema10 < ema20 < ema50:
            signals.append("🔴 تحت EMA10/20/50 — هابط")
            sell_score += 2
        else:
            signals.append("🟡 بين المتوسطات — محايد")

        # MACD
        if macd_val > macd_sig and macd_val > 0:
            signals.append("🟢 MACD فوق الصفر والـ Signal")
            buy_score += 1
        elif macd_val > macd_sig:
            signals.append("🟡 MACD فوق الـ Signal")
            buy_score += 1
        else:
            signals.append("🔴 MACD تحت الـ Signal")
            sell_score += 1

        # قوة الإشارة
        if buy_score >= 4:
            strength = "🚀 شراء قوي جداً"
        elif buy_score >= 2:
            strength = "✅ فرصة شراء"
        elif sell_score >= 3:
            strength = "🛑 بيع قوي"
        elif sell_score >= 2:
            strength = "⚠️ إشارة بيع"
        else:
            strength = "➡️ محايد"

        return {
            "symbol":      symbol,
            "name":        NAMES.get(symbol, symbol),
            "price":       price,
            "change_pct":  change_pct,
            "rsi":         rsi,
            "ema10":       ema10,
            "ema20":       ema20,
            "ema50":       ema50,
            "ema200":      ema200,
            "signals":     signals,
            "strength":    strength,
            "buy_score":   buy_score,
            "sell_score":  sell_score,
            "ema10_cross": ema10_cross
        }

    except Exception as e:
        print(f"خطأ {symbol}: {e}")
        return None

# ── تشغيل الـ Screener ───────────────────────────────
def run_screener():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*40}")
    print(f"تشغيل السوق السعودي — {now}")
    print(f"{'='*40}")

    buy_strong = []
    buy_normal = []
    sell_list  = []
    cross_list = []

    for symbol in TADAWUL30:
        print(f"تحليل {symbol}...")
        result = analyze_stock(symbol)
        if result:
            if result["ema10_cross"]:
                cross_list.append(result)
            if result["buy_score"] >= 4:
                buy_strong.append(result)
            elif result["buy_score"] >= 2:
                buy_normal.append(result)
            elif result["sell_score"] >= 2:
                sell_list.append(result)
        time.sleep(0.5)

    # ترتيب
    buy_strong.sort(key=lambda x: x["buy_score"], reverse=True)
    buy_normal.sort(key=lambda x: x["buy_score"], reverse=True)
    sell_list.sort(key=lambda x: x["sell_score"], reverse=True)

    # ── تقاطعات EMA10/EMA20 ───────────────────────────
    if cross_list:
        msg  = f"⭐ <b>تقاطع EMA10 فوق EMA20 — تداول</b>\n"
        msg += f"🕐 {now}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in cross_list:
            arrow = "📈" if r['change_pct'] > 0 else "📉"
            msg += (
                f"📌 <b>{r['name']}</b> ({r['symbol']})\n"
                f"💰 {r['price']} ر.س {arrow} {r['change_pct']}%\n"
                f"   RSI: {r['rsi']} | EMA10: {r['ema10']} | EMA20: {r['ema20']}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── شراء قوي ─────────────────────────────────────
    if buy_strong:
        msg  = f"🚀 <b>إشارات شراء قوية — تداول 30</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_strong[:8]:
            arrow = "📈" if r['change_pct'] > 0 else "📉"
            msg += (
                f"📌 <b>{r['name']}</b> ({r['symbol']})\n"
                f"💰 {r['price']} ر.س {arrow} {r['change_pct']}%\n"
                f"   RSI: {r['rsi']}\n"
                f"   EMA10: {r['ema10']} | EMA20: {r['ema20']}\n"
                f"   EMA50: {r['ema50']} | EMA200: {r['ema200']}\n"
                f"   {chr(10).join(r['signals'])}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── فرص شراء ─────────────────────────────────────
    if buy_normal:
        msg  = f"✅ <b>فرص شراء — تداول 30</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_normal[:8]:
            arrow = "📈" if r['change_pct'] > 0 else "📉"
            msg += (
                f"📌 <b>{r['name']}</b> ({r['symbol']})\n"
                f"💰 {r['price']} ر.س {arrow} {r['change_pct']}%\n"
                f"   RSI: {r['rsi']} | EMA50: {r['ema50']}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── إشارات بيع ───────────────────────────────────
    if sell_list:
        msg  = f"⚠️ <b>إشارات بيع — تداول 30</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in sell_list[:8]:
            arrow = "📈" if r['change_pct'] > 0 else "📉"
            msg += (
                f"📌 <b>{r['name']}</b> ({r['symbol']})\n"
                f"💰 {r['price']} ر.س {arrow} {r['change_pct']}%\n"
                f"   RSI: {r['rsi']} | EMA50: {r['ema50']}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── لا إشارات ────────────────────────────────────
    if not buy_strong and not buy_normal and not sell_list and not cross_list:
        send_telegram(
            f"📊 <b>Screener تداول 30</b>\n"
            f"🕐 {now} | فريم يومي\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"➡️  لا توجد إشارات واضحة الآن للسوق السعودى"
        )

    print("✅ اكتمل")


# ── تشغيل ────────────────────────────────────────────
if __name__ == "__main__":
    send_telegram(
        "✅ <b>بوت السوق السعودي</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 تداول 30 | فريم يومي\n"
        "📈 EMA10 / EMA20 / EMA50 / EMA200\n"
        "📉 RSI + MACD\n"
        "⏰ كل 10 دقيقة\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "جاري التحليل..."
    )

    run_screener()

    schedule.every(10).minutes.do(run_screener)

    while True:
        schedule.run_pending()
        time.sleep(1)
