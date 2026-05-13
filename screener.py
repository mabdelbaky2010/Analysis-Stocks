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

# ── قائمة الأسهم المحدثة ─────────────────────────────
STOCKS = {
    # ── تداول 30 (بعد الحذف) ──────────────────────────
    "2222.SR": "أرامكو",
    "1120.SR": "الراجحي",
    "2082.SR": "اكوا باور",
    "1140.SR": "البلاد",
    "4031.SR": "الخدمات الأرضية",
    "6004.SR": "كاتريون",
    "4013.SR": "سليمان الحبيب",
    "1322.SR": "أماك",
    "1111.SR": "تداول",
    "2381.SR": "الحفر",
    "2170.SR": "اللجين",
    "2382.SR": "أديس",
}

# ── إرسال تيليجرام ───────────────────────────────────
def send_telegram(message):
    url = f"https://api.telegram.org/bot8784816733:AAF2FpH9EqJ85BzVUjSXH1UI4McDIhSbNvI/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"خطأ تيليجرام: {e}")

# ── تحليل سهم ────────────────────────────────────────
def analyze(symbol, name):
    try:
        df = yf.download(symbol, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 25:
            return None

        df["EMA10"] = ta.ema(df["Close"], length=10)
        df["EMA20"] = ta.ema(df["Close"], length=20)
        df["RSI"]   = ta.rsi(df["Close"], length=14)

        last = df.iloc[-1]
        prev = df.iloc[-2]

        price      = round(float(last["Close"]), 2)
        ema10      = round(float(last["EMA10"]), 2)
        ema20      = round(float(last["EMA20"]), 2)
        rsi        = round(float(last["RSI"]), 1)
        change_pct = round(((price - float(prev["Close"])) / float(prev["Close"])) * 100, 2)

        # ── تقاطع صاعد ────────────────────────────────
        cross_up = (
            float(prev["EMA10"]) <= float(prev["EMA20"]) and
            float(last["EMA10"]) >  float(last["EMA20"])
        )

        # ── تقاطع هابط ────────────────────────────────
        cross_down = (
            float(prev["EMA10"]) >= float(prev["EMA20"]) and
            float(last["EMA10"]) <  float(last["EMA20"])
        )

        ema10_above = ema10 > ema20

        # ── تحليل RSI ─────────────────────────────────
        if rsi < 30:
            rsi_signal = "🔵 تشبع بيع قوي"
            rsi_score  = 3
        elif rsi < 40:
            rsi_signal = "🔵 تشبع بيع"
            rsi_score  = 2
        elif 40 <= rsi <= 60:
            rsi_signal = "⚪ محايد"
            rsi_score  = 0
        elif 60 < rsi <= 70:
            rsi_signal = "🟡 قوي — راقب التشبع"
            rsi_score  = 1
        else:
            rsi_signal = "🔴 تشبع شراء"
            rsi_score  = -2

        return {
            "symbol":      symbol,
            "name":        name,
            "price":       price,
            "change_pct":  change_pct,
            "ema10":       ema10,
            "ema20":       ema20,
            "rsi":         rsi,
            "rsi_signal":  rsi_signal,
            "rsi_score":   rsi_score,
            "cross_up":    cross_up,
            "cross_down":  cross_down,
            "ema10_above": ema10_above,
        }

    except Exception as e:
        print(f"خطأ {symbol}: {e}")
        return None

# ── بناء وإرسال التقرير ──────────────────────────────
def build_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    cross_up_list   = [r for r in results if r["cross_up"]]
    cross_down_list = [r for r in results if r["cross_down"]]
    above_list      = sorted(
        [r for r in results if r["ema10_above"] and not r["cross_up"]],
        key=lambda x: x["rsi_score"], reverse=True
    )

    def fmt(r):
        arrow      = "📈" if r["change_pct"] > 0 else "📉"
        ema_status = "فوق ✅" if r["ema10_above"] else "تحت ❌"
        return (
            f"📌 <b>{r['name']}</b>\n"
            f"   💰 {r['price']} ر.س {arrow} {r['change_pct']}%\n"
            f"   EMA10: {r['ema10']} | EMA20: {r['ema20']} | {ema_status}\n"
            f"   RSI: {r['rsi']} — {r['rsi_signal']}\n\n"
        )

    # ── 1 — تقاطع صاعد اليوم ─────────────────────────
    if cross_up_list:
        msg  = f"⭐ <b>تقاطع صاعد اليوم — EMA10 فوق EMA20</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in cross_up_list:
            msg += fmt(r)
        msg += "📊 EMA10 تجاوز EMA20 لأول مرة اليوم"
        send_telegram(msg)
    else:
        send_telegram(
            f"📊 <b>تقاطع EMA10/EMA20</b>\n"
            f"🕐 {now}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"➡️ لا يوجد تقاطع صاعد جديد اليوم"
        )

    # ── 2 — تقاطع هابط اليوم ─────────────────────────
    if cross_down_list:
        msg  = f"⚠️ <b>تقاطع هابط اليوم — EMA10 تحت EMA20</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in cross_down_list:
            msg += fmt(r)
        send_telegram(msg)

    # ── 3 — أسهم EMA10 فوق EMA20 مع RSI جيد ──────────
    good = [r for r in above_list if r["rsi_score"] >= 1]
    if good:
        msg  = f"✅ <b>EMA10 فوق EMA20 + RSI جيد</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in good[:10]:
            msg += fmt(r)
        send_telegram(msg)

    # ── 4 — ملخص عام ─────────────────────────────────
    total_above = len([r for r in results if r["ema10_above"]])
    total_below = len(results) - total_above

    summary  = f"📋 <b>ملخص اليوم — {now}</b>\n"
    summary += f"━━━━━━━━━━━━━━━━━━\n"
    summary += f"📊 إجمالي الأسهم  : {len(results)}\n"
    summary += f"✅ EMA10 فوق EMA20: {total_above} سهم\n"
    summary += f"❌ EMA10 تحت EMA20: {total_below} سهم\n"
    summary += f"⭐ تقاطع صاعد     : {len(cross_up_list)} سهم\n"
    summary += f"⚠️ تقاطع هابط     : {len(cross_down_list)} سهم\n"
    summary += f"━━━━━━━━━━━━━━━━━━\n"

    if total_above > 0:
        names = " | ".join([r["name"] for r in results if r["ema10_above"]])
        summary += f"📈 الأسهم فوق EMA:\n{names}"

    send_telegram(summary)

# ── تشغيل السكربت ────────────────────────────────────
def run():
    now = datetime.now().strftime("%H:%M")
    print(f"\n{'='*40}\n🇸🇦 تداول — {now}\n{'='*40}")

    results = []
    for symbol, name in STOCKS.items():
        print(f"  تحليل {name}...")
        r = analyze(symbol, name)
        if r:
            results.append(r)
        time.sleep(0.5)

    if results:
        build_report(results)
    else:
        send_telegram("⚠️ لم يتم جلب أي بيانات — تحقق من الاتصال")

    print("✅ اكتمل التحليل")

# ── الجدول الزمني ────────────────────────────────────
if __name__ == "__main__":
    send_telegram(
        "✅ <b>بوت تداول — يومي</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 الفلاتر:\n"
        "   • تقاطع EMA10 / EMA20 اليومي\n"
        "   • تحليل RSI\n"
        f"📋 عدد الأسهم: {len(STOCKS)}\n"
        "⏰ يعمل كل يوم الساعة 4:00 مساءً\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔄 جاري التحليل الأول..."
    )

    run()

    schedule.every(10).mintues.do(run)

    while True:
        schedule.run_pending()
        time.sleep(1)
