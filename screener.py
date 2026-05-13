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
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"خطأ تيليجرام: {e}")

# ─────────────────────────────────────────────────────
# تحليل NASDAQ — فريم ساعة
# ─────────────────────────────────────────────────────
def analyze_nasdaq(symbol, name=None):
    try:
        df = yf.download(symbol, period="3mo", interval="1h", progress=False)
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
            "symbol": symbol, "name": name or symbol,
            "price": price, "change_pct": change_pct,
            "rsi": rsi, "ema10": ema10, "ema20": ema20,
            "ema50": ema50, "ema200": ema200,
            "signals": signals, "strength": strength,
            "buy_score": buy_score, "sell_score": sell_score,
            "ema10_cross": ema10_cross,
        }
    except Exception as e:
        print(f"خطأ {symbol}: {e}")
        return None

# ─────────────────────────────────────────────────────
# تحليل السوق السعودي — فريم أسبوعي + شرط EMA10>EMA20 يومي
# ─────────────────────────────────────────────────────
def analyze_saudi(symbol, name=None):
    try:
        # ── فريم أسبوعي للمضاربة ──────────────────────
        df_week = yf.download(symbol, period="2y",  interval="1wk", progress=False)
        # ── فريم يومي لشرط EMA10 > EMA20 ─────────────
        df_day  = yf.download(symbol, period="6mo", interval="1d",  progress=False)

        if df_week.empty or len(df_week) < 30:
            return None
        if df_day.empty or len(df_day) < 25:
            return None

        # ── مؤشرات الفريم الأسبوعي ────────────────────
        df_week["EMA9"]   = ta.ema(df_week["Close"], length=9)
        df_week["EMA21"]  = ta.ema(df_week["Close"], length=21)
        df_week["EMA50"]  = ta.ema(df_week["Close"], length=50)
        df_week["RSI"]    = ta.rsi(df_week["Close"], length=14)

        macd = ta.macd(df_week["Close"], fast=12, slow=26, signal=9)
        df_week["MACD"]        = macd["MACD_12_26_9"]
        df_week["MACD_SIGNAL"] = macd["MACDs_12_26_9"]

        stoch = ta.stoch(df_week["High"], df_week["Low"], df_week["Close"], k=14, d=3)
        df_week["STOCH_K"] = stoch["STOCHk_14_3_3"]
        df_week["STOCH_D"] = stoch["STOCHd_14_3_3"]

        df_week["VOL_MA20"] = df_week["Volume"].rolling(20).mean()

        # ── مؤشرات الفريم اليومي ──────────────────────
        df_day["EMA10"] = ta.ema(df_day["Close"], length=10)
        df_day["EMA20"] = ta.ema(df_day["Close"], length=20)

        # ── آخر شمعة أسبوعية ──────────────────────────
        last_w = df_week.iloc[-1]
        prev_w = df_week.iloc[-2]

        # ── آخر شمعة يومية ────────────────────────────
        last_d = df_day.iloc[-1]

        price      = round(float(last_w["Close"]), 2)
        rsi        = round(float(last_w["RSI"]), 1)
        ema9       = round(float(last_w["EMA9"]), 2)
        ema21      = round(float(last_w["EMA21"]), 2)
        ema50      = round(float(last_w["EMA50"]), 2)
        macd_val   = round(float(last_w["MACD"]), 4)
        macd_sig   = round(float(last_w["MACD_SIGNAL"]), 4)
        stoch_k    = round(float(last_w["STOCH_K"]), 1)
        stoch_d    = round(float(last_w["STOCH_D"]), 1)
        volume     = float(last_w["Volume"])
        vol_ma     = float(last_w["VOL_MA20"])
        change_pct = round(((price - float(prev_w["Close"])) / float(prev_w["Close"])) * 100, 2)

        # ── EMA10 و EMA20 اليومي ──────────────────────
        ema10_day = round(float(last_d["EMA10"]), 2)
        ema20_day = round(float(last_d["EMA20"]), 2)

        # ── الشرط الأساسي: EMA10 فوق EMA20 يومي ──────
        ema10_above_ema20 = ema10_day > ema20_day

        # ── لو EMA10 تحت EMA20 — تجاهل السهم ─────────
        if not ema10_above_ema20:
            return None

        # ── تقاطعات أسبوعية ───────────────────────────
        ema9_cross = (
            float(prev_w["EMA9"]) < float(prev_w["EMA21"]) and
            float(last_w["EMA9"]) > float(last_w["EMA21"])
        )
        macd_cross = (
            float(prev_w["MACD"]) < float(prev_w["MACD_SIGNAL"]) and
            float(last_w["MACD"]) > float(last_w["MACD_SIGNAL"])
        )

        signals    = []
        buy_score  = 0
        sell_score = 0

        # ① EMA10 فوق EMA20 يومي — شرط أساسي
        signals.append(f"✅ EMA10({ema10_day}) فوق EMA20({ema20_day}) — يومي")
        buy_score += 2

        # ② RSI أسبوعي
        if 45 <= rsi <= 65:
            signals.append(f"🟢 RSI مثالي {rsi}")
            buy_score += 1
        elif rsi < 35:
            signals.append(f"🔵 RSI تشبع بيع {rsi} — فرصة ارتداد")
            buy_score += 2
        elif rsi > 70:
            signals.append(f"🔴 RSI تشبع شراء {rsi}")
            sell_score += 2
        else:
            signals.append(f"⚪ RSI محايد {rsi}")

        # ③ تقاطع EMA9 فوق EMA21 أسبوعي
        if ema9_cross:
            signals.append("⭐ تقاطع EMA9 فوق EMA21 أسبوعي!")
            buy_score += 3

        # ④ EMA الاتجاه الأسبوعي
        if price > ema9 > ema21 > ema50:
            signals.append("🟢 فوق EMA9/21/50 — صاعد قوي")
            buy_score += 2
        elif price > ema21 > ema50:
            signals.append("🟢 فوق EMA21/50 — صاعد")
            buy_score += 1
        elif price < ema9 < ema21:
            signals.append("🔴 تحت EMA9/21 — هابط")
            sell_score += 2
        else:
            signals.append("🟡 بين المتوسطات")

        # ⑤ MACD أسبوعي
        if macd_cross:
            signals.append("⭐ تقاطع MACD صاعد أسبوعي!")
            buy_score += 2
        elif macd_val > macd_sig and macd_val > 0:
            signals.append("🟢 MACD فوق الصفر والـ Signal")
            buy_score += 1
        elif macd_val > macd_sig:
            signals.append("🟡 MACD فوق الـ Signal")
            buy_score += 1
        else:
            signals.append("🔴 MACD تحت الـ Signal")
            sell_score += 1

        # ⑥ Stochastic
        if stoch_k > stoch_d and stoch_k < 40:
            signals.append(f"🟢 Stochastic خروج من تشبع بيع K:{stoch_k}")
            buy_score += 2
        elif stoch_k > stoch_d and stoch_k < 60:
            signals.append(f"🟢 Stochastic صاعد K:{stoch_k}")
            buy_score += 1
        elif stoch_k > 80:
            signals.append(f"🔴 Stochastic تشبع شراء K:{stoch_k}")
            sell_score += 1

        # ⑦ حجم التداول
        if vol_ma > 0 and volume > vol_ma * 1.3:
            signals.append("🟢 حجم تداول قوي فوق المتوسط")
            buy_score += 1
        elif vol_ma > 0 and volume < vol_ma * 0.7:
            signals.append("🟡 حجم تداول ضعيف")

        # ── قوة الإشارة ───────────────────────────────
        if buy_score >= 8:
            strength = "🔥 فرصة مضاربة أسبوعية ممتازة"
        elif buy_score >= 6:
            strength = "🚀 إشارة مضاربة قوية"
        elif buy_score >= 4:
            strength = "✅ فرصة مضاربة"
        elif sell_score >= 4:
            strength = "🛑 إشارة بيع قوية"
        elif sell_score >= 2:
            strength = "⚠️ إشارة بيع"
        else:
            strength = "➡️ محايد"

        return {
            "symbol":           symbol,
            "name":             name or symbol,
            "price":            price,
            "change_pct":       change_pct,
            "rsi":              rsi,
            "ema9":             ema9,
            "ema21":            ema21,
            "ema50":            ema50,
            "ema10_day":        ema10_day,
            "ema20_day":        ema20_day,
            "stoch_k":          stoch_k,
            "stoch_d":          stoch_d,
            "signals":          signals,
            "strength":         strength,
            "buy_score":        buy_score,
            "sell_score":       sell_score,
            "ema9_cross":       ema9_cross,
            "macd_cross":       macd_cross,
            "ema10_above_ema20": ema10_above_ema20,
        }
    except Exception as e:
        print(f"خطأ {symbol}: {e}")
        return None

# ─────────────────────────────────────────────────────
# تقرير NASDAQ
# ─────────────────────────────────────────────────────
def build_nasdaq_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    buy_strong = sorted([r for r in results if r["buy_score"] >= 4],     key=lambda x: x["buy_score"],  reverse=True)
    buy_normal = sorted([r for r in results if 2 <= r["buy_score"] < 4], key=lambda x: x["buy_score"],  reverse=True)
    sell_list  = sorted([r for r in results if r["sell_score"] >= 2],    key=lambda x: x["sell_score"], reverse=True)
    cross_list = [r for r in results if r["ema10_cross"]]

    def fmt(r):
        arrow = "📈" if r["change_pct"] > 0 else "📉"
        return (
            f"📌 <b>{r['name']}</b>\n"
            f"   💰 ${r['price']} {arrow} {r['change_pct']}%\n"
            f"   RSI: {r['rsi']} | EMA10: {r['ema10']} | EMA50: {r['ema50']}\n"
            f"   {' | '.join(r['signals'])}\n"
            f"   {r['strength']}\n\n"
        )

    if cross_list:
        msg = f"⭐ <b>تقاطع EMA10/EMA20 — NASDAQ</b>\n🕐 {now} | فريم ساعة ⏱\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in cross_list: msg += fmt(r)
        send_telegram(msg)

    if buy_strong:
        msg = f"🚀 <b>شراء قوي — NASDAQ 100</b>\n🕐 {now} | فريم ساعة ⏱\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_strong[:8]: msg += fmt(r)
        send_telegram(msg)

    if buy_normal:
        msg = f"✅ <b>فرص شراء — NASDAQ 100</b>\n🕐 {now} | فريم ساعة ⏱\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in buy_normal[:8]: msg += fmt(r)
        send_telegram(msg)

    if sell_list:
        msg = f"⚠️ <b>إشارات بيع — NASDAQ 100</b>\n🕐 {now} | فريم ساعة ⏱\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in sell_list[:8]: msg += fmt(r)
        send_telegram(msg)

    if not any([buy_strong, buy_normal, sell_list, cross_list]):
        send_telegram(f"📊 <b>NASDAQ 100</b>\n🕐 {now}\n━━━━━━━━━━━━━━━━━━\n➡️ لا توجد إشارات الآن")

# ─────────────────────────────────────────────────────
# تقرير تداول الأسبوعي
# ─────────────────────────────────────────────────────
def build_saudi_report(results):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    excellent = sorted([r for r in results if r["buy_score"] >= 8],     key=lambda x: x["buy_score"],  reverse=True)
    strong    = sorted([r for r in results if 6 <= r["buy_score"] < 8], key=lambda x: x["buy_score"],  reverse=True)
    normal    = sorted([r for r in results if 4 <= r["buy_score"] < 6], key=lambda x: x["buy_score"],  reverse=True)
    sell_list = sorted([r for r in results if r["sell_score"] >= 2],    key=lambda x: x["sell_score"], reverse=True)
    crosses   = [r for r in results if r["ema9_cross"] or r["macd_cross"]]

    def fmt(r):
        arrow     = "📈" if r["change_pct"] > 0 else "📉"
        cross_tag = ""
        if r["ema9_cross"]:  cross_tag += " ⭐EMA"
        if r["macd_cross"]:  cross_tag += " ⭐MACD"
        return (
            f"📌 <b>{r['name']}</b> ({r['symbol']}){cross_tag}\n"
            f"   💰 {r['price']} ر.س {arrow} {r['change_pct']}%\n"
            f"   RSI: {r['rsi']} | Stoch K:{r['stoch_k']} D:{r['stoch_d']}\n"
            f"   EMA9: {r['ema9']} | EMA21: {r['ema21']} | EMA50: {r['ema50']}\n"
            f"   📅 EMA10({r['ema10_day']}) فوق EMA20({r['ema20_day']}) ✅\n"
            f"   {chr(10).join(r['signals'])}\n"
            f"   {r['strength']}\n\n"
        )

    if not results:
        send_telegram(
            f"📊 <b>تداول 30</b>\n"
            f"🕐 {now} | فريم أسبوعي 📅\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"➡️ لا توجد أسهم EMA10 فوق EMA20 يومياً الآن"
        )
        return

    # ملخص الأسهم المؤهلة
    names = " | ".join([r["name"] for r in results])
    send_telegram(
        f"🔍 <b>أسهم اجتازت الفلتر اليومي</b>\n"
        f"🕐 {now}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ EMA10 فوق EMA20 (يومي): {len(results)} سهم\n"
        f"{names}"
    )

    if crosses:
        msg = f"⭐ <b>تقاطعات هذا الأسبوع — تداول 30</b>\n🕐 {now} | فريم أسبوعي 📅\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in crosses: msg += fmt(r)
        send_telegram(msg)

    if excellent:
        msg = f"🔥 <b>فرص مضاربة ممتازة — تداول 30</b>\n🕐 {now} | فريم أسبوعي 📅\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in excellent[:5]: msg += fmt(r)
        send_telegram(msg)

    if strong:
        msg = f"🚀 <b>إشارات مضاربة قوية — تداول 30</b>\n🕐 {now} | فريم أسبوعي 📅\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in strong[:5]: msg += fmt(r)
        send_telegram(msg)

    if normal:
        msg = f"✅ <b>فرص مضاربة — تداول 30</b>\n🕐 {now} | فريم أسبوعي 📅\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in normal[:5]: msg += fmt(r)
        send_telegram(msg)

    if sell_list:
        msg = f"⚠️ <b>إشارات بيع — تداول 30</b>\n🕐 {now} | فريم أسبوعي 📅\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in sell_list[:5]: msg += fmt(r)
        send_telegram(msg)

# ─────────────────────────────────────────────────────
# تشغيل NASDAQ — كل 15 دقيقة
# ─────────────────────────────────────────────────────
def run_nasdaq():
    print(f"\n{'='*40}\n🇺🇸 NASDAQ — {datetime.now().strftime('%H:%M')}\n{'='*40}")
    results = []
    for symbol in NASDAQ100:
        print(f"  {symbol}...")
        r = analyze_nasdaq(symbol, name=symbol)
        if r:
            results.append(r)
        time.sleep(0.5)
    build_nasdaq_report(results)
    print("✅ NASDAQ اكتمل")

# ─────────────────────────────────────────────────────
# تشغيل تداول — كل أحد
# ─────────────────────────────────────────────────────
def run_saudi():
    print(f"\n{'='*40}\n🇸🇦 تداول — {datetime.now().strftime('%H:%M')}\n{'='*40}")
    results = []
    for symbol in TADAWUL30:
        print(f"  {symbol}...")
        r = analyze_saudi(symbol, name=TADAWUL_NAMES.get(symbol, symbol))
        if r:
            results.append(r)
        time.sleep(0.5)
    build_saudi_report(results)
    print("✅ تداول اكتمل")

# ─────────────────────────────────────────────────────
# الجدول الزمني
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    send_telegram(
        "✅ <b>بوت الأسواق المالية</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 NASDAQ 100 — كل 15 دقيقة | فريم ساعة ⏱\n"
        "🇸🇦 تداول 30  — كل أحد 9:30 ص | فريم أسبوعي 📅\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🇸🇦 فلتر: EMA10 فوق EMA20 يومي ✅\n"
        "🇸🇦 تحليل: EMA9/21/50 | RSI | MACD | Stochastic | Volume\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔄 جاري التحليل..."
    )

    # تشغيل فوري عند البدء
    threading.Thread(target=run_nasdaq).start()
    threading.Thread(target=run_saudi).start()

    # NASDAQ كل 15 دقيقة
    schedule.every(15).minutes.at("16:00")do(
        lambda: threading.Thread(target=run_nasdaq).start()
    )

    # تداول كل أحد الساعة 9:30 صباحاً
    schedule.every(10).mintues.at("12:30").do(
        lambda: threading.Thread(target=run_saudi).start()
    )

    while True:
        schedule.run_pending()
        time.sleep(1)
