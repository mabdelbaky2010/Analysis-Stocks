import requests
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from datetime import datetime
import time
import schedule
import threading

# ── إعدادات ──────────────────────────────────────────
TELEGRAM_TOKEN = "8784816733:AAF2FpH9EqJ85BzVUjSXH1UI4McDIhSbNvI"
CHAT_ID        = "1621604072"

# ── قوائم الأسهم ─────────────────────────────────────
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

TADAWUL30 = [
    "2222.SR","1180.SR","1120.SR","2010.SR","2350.SR",
    "7010.SR","7020.SR","7030.SR","2330.SR","4200.SR",
    "1010.SR","1050.SR","1060.SR","1080.SR","1150.SR",
    "2001.SR","2020.SR","2060.SR","2290.SR","2380.SR",
    "3010.SR","3030.SR","3160.SR","4001.SR","4030.SR",
    "4050.SR","4161.SR","4240.SR","6010.SR","8010.SR",
]

TADAWUL_NAMES = {
    "2222.SR":"أرامكو","1180.SR":"الأهلي","1120.SR":"الراجحي",
    "2010.SR":"سابك","2350.SR":"المملكة القابضة","7010.SR":"الاتصالات",
    "7020.SR":"موبايلي","7030.SR":"زين","2330.SR":"أدفانسد",
    "4200.SR":"بنك البلاد","1010.SR":"الرياض","1050.SR":"السعودي الفرنسي",
    "1060.SR":"السعودي للاستثمار","1080.SR":"Arab National","1150.SR":"الجزيرة",
    "2001.SR":"المتقدمة","2020.SR":"سبكيم","2060.SR":"إيثيلين",
    "2290.SR":"أبوقير","2380.SR":"بترو رابغ","3010.SR":"سيمنس العربية",
    "3030.SR":"بوان","3160.SR":"المراعي","4001.SR":"التأمين العربي",
    "4030.SR":"ميدغلف","4050.SR":"المتحدة","4161.SR":"تكافل الراجحي",
    "4240.SR":"بوبا العربية","6010.SR":"سابتا","8010.SR":"معادن",
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
def analyze_stock(symbol, name=None, interval="1d", period="1y"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False)
        if df.empty or len(df) < 50:
            return None

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

        price      = round(float(last["Close"]), 2)
        rsi        = round(float(last["RSI"]), 1)
        ema10      = round(float(last["EMA10"]), 2)
        ema20      = round(float(last["EMA20"]), 2)
        ema50      = round(float(last["EMA50"]), 2)
        ema200     = round(float(last["EMA200"]), 2)
        macd_val   = round(float(last["MACD"]), 4)
        macd_sig   = round(float(last["MACD_SIGNAL"]), 4)
        change_pct = round(((price - float(prev["Close"])) / float(prev["Close"])) * 100, 2)

        ema10_cross = (
            float(prev["EMA10"]) < float(prev["EMA20"]) and
            float(last["EMA10"]) > float(last["EMA20"])
        )

        signals    = []
        buy_score  = 0
        sell_score = 0

        if rsi < 40:
            signals.append("🔵 RSI تشبع بيع")
            buy_score += 1
        elif rsi > 65:
            signals.append("🔴 RSI تشبع شراء")
            sell_score += 1
        else:
            signals.append(f"⚪ RSI محايد {rsi}")

        if ema10_cross:
            signals.append("⭐ تقاطع EMA10 فوق EMA20")
            buy_score += 2

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
            signals.append("🟡 بين المتوسطات")

        if macd_val > macd_sig and macd_val > 0:
            signals.append("🟢 MACD فوق الصفر والـ Signal")
            buy_score += 1
        elif macd_val > macd_sig:
            signals.append("🟡 MACD فوق الـ Signal")
            buy_score += 1
        else:
            signals.append("🔴 MACD تحت الـ Signal")
            sell_score += 1

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
            "name":        name or symbol,
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
            "ema10_cross": ema10_cross,
        }
    except Exception as e:
        print(f"خطأ {symbol}: {e}")
        return None

# ── بناء وإرسال التقرير ──────────────────────────────
def build_and_send(results, market_name, currency, timeframe):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    buy_strong = sorted([r for r in results if r["buy_score"] >= 4],      key=lambda x: x["buy_score"],  reverse=True)
    buy_normal = sorted([r for r in results if 2 <= r["buy_score"] < 4],  key=lambda x: x["buy_score"],  reverse=True)
    sell_list  = sorted([r for r in results if r["sell_score"] >= 2],     key=lambda x: x["sell_score"], reverse=True)
    cross_list = [r for r in results if r["ema10_cross"]]

    def fmt(r):
        arrow = "📈" if r["change_pct"] > 0 else "📉"
        return (
            f"📌 <b>{r['name']}</b>\n"
            f"   💰 {r['price']} {currency} {arrow} {r['change_pct']}%\n"
            f"   RSI: {r['rsi']} | EMA10: {r['ema10']} | EMA50: {r['ema50']}\n"
            f"   {' | '.join(r['signals'])}\n"
            f"   {r['strength']}\n\n"
        )

    if cross_list:
        msg = f"⭐ <b>تقاطع EMA10/EMA20 — {market_name}</b>\n🕐 {now} | {timeframe}\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in cross_list:
            msg += fmt(r)
        send_telegram(msg)

    if buy_strong:
        msg = f"🚀 <b>شراء قوي — {market_name}</b>\n🕐 {now} | {timeframe}\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_strong[:8]:
            msg += fmt(r)
        send_telegram(msg)

    if buy_normal:
        msg = f"✅ <b>فرص شراء — {market_name}</b>\n🕐 {now} | {timeframe}\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_normal[:8]:
            msg += fmt(r)
        send_telegram(msg)

    if sell_list:
        msg = f"⚠️ <b>إشارات بيع — {market_name}</b>\n🕐 {now} | {timeframe}\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in sell_list[:8]:
            msg += fmt(r)
        send_telegram(msg)

    if not any([buy_strong, buy_normal, sell_list, cross_list]):
        send_telegram(
            f"📊 <b>{market_name}</b>\n"
            f"🕐 {now} | {timeframe}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"➡️ لا توجد إشارات الآن"
        )

# ── NASDAQ — كل 15 دقيقة — فريم ساعة ────────────────
def run_nasdaq():
    print(f"\n{'='*40}\n🇺🇸 NASDAQ — {datetime.now().strftime('%H:%M')}\n{'='*40}")
    results = []
    for symbol in NASDAQ100:
        print(f"  {symbol}...")
        r = analyze_stock(
            symbol,
            name=symbol,
            interval="1h",   # ← فريم ساعة
            period="3mo"
        )
        if r:
            results.append(r)
        time.sleep(0.5)
    build_and_send(results, "NASDAQ 100", "$", "فريم ساعة ⏱")
    print("✅ NASDAQ اكتمل")

# ── تداول 30 — مرة واحدة يومياً — فريم يوم ──────────
def run_saudi():
    print(f"\n{'='*40}\n🇸🇦 تداول — {datetime.now().strftime('%H:%M')}\n{'='*40}")
    results = []
    for symbol in TADAWUL30:
        print(f"  {symbol}...")
        r = analyze_stock(
            symbol,
            name=TADAWUL_NAMES.get(symbol, symbol),
            interval="1d",   # ← فريم يوم
            period="1y"
        )
        if r:
            results.append(r)
        time.sleep(0.5)
    build_and_send(results, "تداول 30", "ر.س", "فريم يومي 📅")
    print("✅ تداول اكتمل")

# ── الجدول الزمني ────────────────────────────────────
if __name__ == "__main__":
    send_telegram(
        "✅ <b>بوت الأسواق المالية</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 NASDAQ 100 — كل 15 دقيقة | فريم ساعة\n"
        "🇸🇦 تداول 30  — مرة يومياً   | فريم يوم\n"
        "📈 EMA10/20/50/200 | RSI | MACD\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔄 جاري التحليل..."
    )

    # تشغيل فوري عند البدء
    threading.Thread(target=run_nasdaq).start()
    threading.Thread(target=run_saudi).start()

    # NASDAQ كل 15 دقيقة
    schedule.every(15).minutes.do(
        lambda: threading.Thread(target=run_nasdaq).start()
    )

    # تداول مرة يومياً الساعة 10 صباحاً (بداية السوق السعودي)
    schedule.every().day.at("10:00").do(
        lambda: threading.Thread(target=run_saudi).start()
    )

    while True:
        schedule.run_pending()
        time.sleep(1)
