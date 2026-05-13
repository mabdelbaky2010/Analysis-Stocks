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

# أسهم NASDAQ 100
NASDAQ100 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","COST",
    "NFLX","AMD","ADBE","QCOM","PEP","TMUS","AMAT","TXN","INTU","CSCO",
    "AMGN","CMCSA","HON","INTC","VRTX","BKNG","SBUX","GILD","ADI","MDLZ",
    "LRCX","REGN","PDD","KLAC","SNPS","MRVL","CDNS","ADP","PANW","FTNT",
    "ABNB","CRWD","MELI","ORLY","ASML","CTAS","CSX","MNST","PCAR","NXPI",
    "PYPL","WDAY","KDP","DXCM","CHTR","ROST","ODFL","FANG","FAST","PAYX",
    "CPRT","VRSK","TEAM","DDOG","ZS","ANSS","SGEN","IDXX","BIIB","ILMN",
    "ALGN","MTCH","LCID","ZM","OKTA","DLTR","SIRI","WBA","EBAY","JD",
    "CTSH","SPLK","ENPH","CEG","ON","GFS","RIVN","GEHC","DASH","TTD",
    "RBLX","GRAB","MCHP","MRNA","LULU","MDB","TTWO","NTES","BMRN","SMCI"
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

# ── تحليل سهم واحد ───────────────────────────────────
def analyze_stock(symbol):
    try:
        # ── فريم يومي — مناسب للاستثمار متوسط المدى ──
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 50:
            return None

        # ── حساب المؤشرات ─────────────────────────────
        df["EMA10"]  = ta.ema(df["Close"], length=10)
        df["EMA20"]  = ta.ema(df["Close"], length=20)
        df["EMA50"]  = ta.ema(df["Close"], length=50)
        df["EMA200"] = ta.ema(df["Close"], length=200)
        df["RSI"]    = ta.rsi(df["Close"], length=14)

        macd = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        df["MACD"]        = macd["MACD_12_26_9"]
        df["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

        # ── آخر يومين للكشف عن التقاطع ────────────────
        last  = df.iloc[-1]
        prev  = df.iloc[-2]

        price    = round(float(last["Close"]), 2)
        rsi      = round(float(last["RSI"]), 1)
        ema10    = round(float(last["EMA10"]), 2)
        ema20    = round(float(last["EMA20"]), 2)
        ema50    = round(float(last["EMA50"]), 2)
        ema200   = round(float(last["EMA200"]), 2)
        macd_val = round(float(last["MACD"]), 4)
        macd_sig = round(float(last["MACD_SIGNAL"]), 4)

        # ── نسبة التغيير اليومي ────────────────────────
        prev_close  = round(float(prev["Close"]), 2)
        change_pct  = round(((price - prev_close) / prev_close) * 100, 2)

        # ── كشف تقاطع EMA10 فوق EMA20 (إشارة دخول) ───
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

        # EMA10 تقاطع EMA20 — إشارة دخول مبكرة
        if ema10_cross:
            signals.append("⭐ EMA10 تقاطع فوق EMA20 — إشارة دخول!")
            buy_score += 2  # وزن أعلى لأنه إشارة واضحة

        # EMA الاتجاه العام
        if price > ema10 > ema20 > ema50 > ema200:
            signals.append("🟢 السعر فوق EMA10/20/50/200 — اتجاه صاعد قوي")
            buy_score += 2
        elif price > ema20 > ema50:
            signals.append("🟢 السعر فوق EMA20/50 — اتجاه صاعد")
            buy_score += 1
        elif price < ema10 < ema20 < ema50:
            signals.append("🔴 السعر تحت EMA10/20/50 — اتجاه هابط")
            sell_score += 2
        else:
            signals.append("🟡 السعر بين المتوسطات — محايد")

        # MACD
        if macd_val > macd_sig and macd_val > 0:
            signals.append("🟢 MACD فوق الصفر وفوق الـ Signal")
            buy_score += 1
        elif macd_val > macd_sig:
            signals.append("🟡 MACD فوق الـ Signal")
            buy_score += 1
        else:
            signals.append("🔴 MACD تحت الـ Signal")
            sell_score += 1

        # ── قوة الإشارة الكلية ────────────────────────
        if buy_score >= 4:
            strength = "🚀 إشارة شراء قوية جداً"
        elif buy_score >= 2:
            strength = "✅ إشارة شراء"
        elif sell_score >= 3:
            strength = "🛑 إشارة بيع قوية"
        elif sell_score >= 2:
            strength = "⚠️ إشارة بيع"
        else:
            strength = "➡️ محايد"

        return {
            "symbol":     symbol,
            "price":      price,
            "change_pct": change_pct,
            "rsi":        rsi,
            "ema10":      ema10,
            "ema20":      ema20,
            "ema50":      ema50,
            "ema200":     ema200,
            "signals":    signals,
            "strength":   strength,
            "buy_score":  buy_score,
            "sell_score": sell_score,
            "ema10_cross": ema10_cross
        }

    except Exception as e:
        print(f"خطأ {symbol}: {e}")
        return None

# ── تشغيل الـ Screener ───────────────────────────────
def run_screener():
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*40}")
    print(f"تشغيل الـ Screener — {now}")
    print(f"{'='*40}")

    buy_strong  = []  # إشارة شراء قوية جداً
    buy_normal  = []  # إشارة شراء عادية
    sell_list   = []  # إشارات بيع
    cross_list  = []  # تقاطعات EMA10/20

    for symbol in NASDAQ100:
        print(f"تحليل {symbol}...")
        result = analyze_stock(symbol)

        if result:
            # تقاطع EMA10 فوق EMA20
            if result["ema10_cross"]:
                cross_list.append(result)

            if result["buy_score"] >= 4:
                buy_strong.append(result)
            elif result["buy_score"] >= 2:
                buy_normal.append(result)
            elif result["sell_score"] >= 2:
                sell_list.append(result)

        time.sleep(0.5)

    # ترتيب حسب قوة الإشارة
    buy_strong.sort(key=lambda x: x["buy_score"], reverse=True)
    buy_normal.sort(key=lambda x: x["buy_score"], reverse=True)
    sell_list.sort(key=lambda x: x["sell_score"], reverse=True)

    # ── إرسال تقاطعات EMA10/EMA20 أولاً ─────────────
    if cross_list:
        msg  = f"⭐ <b>تقاطع EMA10 فوق EMA20 اليوم!</b>\n"
        msg += f"🕐 {now}\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in cross_list:
            chg = r['change_pct']
            arrow = "📈" if chg > 0 else "📉"
            msg += (
                f"📌 <b>{r['symbol']}</b> — ${r['price']} "
                f"{arrow} {chg}%\n"
                f"   RSI: {r['rsi']} | "
                f"EMA10: ${r['ema10']} | "
                f"EMA20: ${r['ema20']}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── إرسال إشارات الشراء القوية ───────────────────
    if buy_strong:
        msg  = f"🚀 <b>إشارات شراء قوية — NASDAQ 100</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_strong[:8]:
            chg = r['change_pct']
            arrow = "📈" if chg > 0 else "📉"
            msg += (
                f"📌 <b>{r['symbol']}</b> — ${r['price']} "
                f"{arrow} {chg}%\n"
                f"   RSI: {r['rsi']} | "
                f"EMA10: ${r['ema10']} | "
                f"EMA20: ${r['ema20']} | "
                f"EMA50: ${r['ema50']}\n"
                f"   {chr(10).join(r['signals'])}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── إرسال إشارات الشراء العادية ──────────────────
    if buy_normal:
        msg  = f"✅ <b>فرص شراء — NASDAQ 100</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_normal[:8]:
            chg = r['change_pct']
            arrow = "📈" if chg > 0 else "📉"
            msg += (
                f"📌 <b>{r['symbol']}</b> — ${r['price']} "
                f"{arrow} {chg}%\n"
                f"   RSI: {r['rsi']} | "
                f"EMA50: ${r['ema50']}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── إرسال إشارات البيع ───────────────────────────
    if sell_list:
        msg  = f"⚠️ <b>إشارات بيع — NASDAQ 100</b>\n"
        msg += f"🕐 {now} | فريم يومي\n"
        msg += f"━━━━━━━━━━━━━━━━━━\n\n"
        for r in sell_list[:8]:
            chg = r['change_pct']
            arrow = "📈" if chg > 0 else "📉"
            msg += (
                f"📌 <b>{r['symbol']}</b> — ${r['price']} "
                f"{arrow} {chg}%\n"
                f"   RSI: {r['rsi']} | "
                f"EMA50: ${r['ema50']}\n"
                f"   {r['strength']}\n\n"
            )
        send_telegram(msg)

    # ── لو ما في إشارات ──────────────────────────────
    if not buy_strong and not buy_normal and not sell_list and not cross_list:
        send_telegram(
            f"📊 <b>Screener NASDAQ 100</b>\n"
            f"🕐 {now} | فريم يومي\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"➡️ لا توجد إشارات واضحة الآن"
        )

    print("✅ اكتمل الـ Screener")


# ── الجدول الزمني ────────────────────────────────────
if __name__ == "__main__":
    send_telegram(
        "✅ <b>بوت الاستثمار متوسط المدى</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📊 NASDAQ 100 | فريم يومي\n"
        "📈 EMA10 / EMA20 / EMA50 / EMA200\n"
        "📉 RSI + MACD\n"
        "⏰ كل 15 دقيقة\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "جاري التحليل..."
    )

    run_screener()

    schedule.every(15).minutes.do(run_screener)

    while True:
        schedule.run_pending()
        time.sleep(1)
