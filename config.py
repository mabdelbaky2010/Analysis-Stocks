"""
ملف الإعدادات - عدّل القيم هنا قبل التشغيل
==============================================

كيفية الحصول على بيانات تليجرام:
1. افتح تليجرام وابحث عن @BotFather
2. أرسل /newbot واتبع التعليمات للحصول على TOKEN
3. ابحث عن @userinfobot وأرسل له /start لمعرفة CHAT_ID الخاص بك
4. أرسل أي رسالة لبوتك الجديد أولاً حتى يستطيع التواصل معك
"""

# ============== إعدادات تليجرام ==============
TELEGRAM_BOT_TOKEN = "8784816733:AAF2FpH9EqJ85BzVUjSXH1UI4McDIhSbNvI"

TELEGRAM_CHAT_ID   = "ضع_الشات_آيدي_هنا"  # مثال"1621604072

# ============== قائمة الأسهم (أكثر أسهم S&P 500 تداولاً) ==============
TICKERS = [
    # Mega Cap Tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",
    # Semis & Tech
    "AMD", "AVGO", "INTC", "QCOM", "MU", "ORCL", "CRM", "ADBE",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "C",
    # Consumer / Retail
    "WMT", "COST", "HD", "NKE", "DIS", "MCD", "SBUX",
    # Energy & Industrials
    "XOM", "CVX", "BA", "CAT", "GE",
    # ETFs
    "SPY", "QQQ", "IWM",
]

# ============== إعدادات الفلتر الفني ==============
LOOKBACK_DAYS    = 2        # عدد الأيام لجلب بيانات 15 دقيقة
INTERVAL         = "15m"    # الفاصل الزمني
VOLUME_SPIKE_MULT = 1.8     # الحجم الحالي مقارنة بمتوسط آخر 20 شمعة (1.8x)
MIN_PRICE        = 2.0      # أقل سعر مقبول للسهم (لتجنب أسهم البنس)
MIN_AVG_VOLUME   = 500_000  # أقل متوسط حجم تداول

# ============== إعدادات تحليل الأخبار ==============
ENABLE_NEWS_ANALYSIS = True
NEWS_LOOKBACK_HOURS  = 12     # الأخبار خلال آخر 12 ساعة
SENTIMENT_THRESHOLD  = 0.20   # عتبة الـ compound score من VADER
MAX_NEWS_PER_TICKER  = 5

# ============== إعدادات الجدولة ==============
RUN_EVERY_MINUTES   = 15
MARKET_OPEN_ET      = "09:30"   # توقيت نيويورك
MARKET_CLOSE_ET     = "16:00"
ONLY_DURING_MARKET  = True     # شغّل فقط خلال ساعات السوق
SEND_HOLD_SIGNALS   = False    # هل ترسل إشارات HOLD أم BUY/SELL فقط؟

# ============== إعدادات إضافية ==============
LOG_FILE       = "stock_bot.log"
SIGNALS_CSV    = "signals_history.csv"
