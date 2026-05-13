"""
Stock Bot - السكربت الرئيسي
==========================
سكربت مضاربة يومية للسوق الأمريكي يعمل كل 15 دقيقة:
  1. يحلل أسهم S&P 500 الأكثر تداولاً
  2. يطبق فلتر VWAP + Volume Spike
  3. يدمج تحليل مشاعر الأخبار (VADER)
  4. يرسل التوصيات لبوت تليجرام

التشغيل:
    python stock_bot.py            # تشغيل دائم خلال ساعات السوق
    python stock_bot.py --once     # دورة واحدة فقط (للاختبار)
    python stock_bot.py --dry-run  # بدون إرسال تليجرام

⚠️ تنبيه: هذا السكربت أداة تحليلية تساعد على اتخاذ القرار، وليس نصيحة استثمارية.
المضاربة اليومية تحمل مخاطر عالية وقد تخسر رأس مالك.
"""

from __future__ import annotations
import argparse
import csv
import logging
import os
import sys
import time
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import config
from technical import analyze_ticker, TechnicalSignal
from news_sentiment import analyze_sentiment, NewsSentiment
from telegram_notifier import send_telegram, send_startup_message, format_signal_message


# ============== Logging ==============
def setup_logging():
    log_path = Path(__file__).parent / config.LOG_FILE
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )

logger = logging.getLogger("StockBot")


# ============== ساعات السوق الأمريكي ==============
ET = ZoneInfo("America/New_York")

def is_market_open(now_et: datetime) -> bool:
    if now_et.weekday() >= 5:   # السبت/الأحد
        return False
    open_h, open_m = map(int, config.MARKET_OPEN_ET.split(":"))
    close_h, close_m = map(int, config.MARKET_CLOSE_ET.split(":"))
    o = dtime(open_h, open_m)
    c = dtime(close_h, close_m)
    return o <= now_et.time() <= c


# ============== دمج الإشارة الفنية والأخبار ==============
def combine_signals(tech: TechnicalSignal, news: NewsSentiment | None) -> tuple[str, str]:
    """
    قواعد الدمج:
    - فني BUY + أخبار BULLISH أو NEUTRAL  → STRONG BUY
    - فني BUY + أخبار BEARISH             → CAUTION (نخفّض إلى HOLD)
    - فني SELL + أخبار BEARISH أو NEUTRAL → STRONG SELL
    - فني SELL + أخبار BULLISH            → HOLD
    - فني HOLD                            → HOLD
    """
    if not news or not news.items:
        return tech.signal, "بدون أخبار حديثة"

    label = news.label
    if tech.signal == "BUY":
        if label in ("BULLISH", "NEUTRAL"):
            return "BUY", f"تأكيد من الأخبار ({label})"
        return "HOLD", f"إشارة فنية شراء لكن الأخبار {label} - حذر"
    if tech.signal == "SELL":
        if label in ("BEARISH", "NEUTRAL"):
            return "SELL", f"تأكيد من الأخبار ({label})"
        return "HOLD", f"إشارة فنية بيع لكن الأخبار {label} - حذر"
    return "HOLD", f"لا توجد قفزة حجم - الأخبار {label}"


# ============== سجل CSV ==============
def append_to_csv(tech: TechnicalSignal, news: NewsSentiment | None, final_signal: str, reason: str):
    csv_path = Path(__file__).parent / config.SIGNALS_CSV
    new_file = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow([
                "timestamp", "ticker", "final_signal", "tech_signal",
                "price", "vwap", "price_vs_vwap_pct", "volume_ratio",
                "news_label", "news_score", "reason"
            ])
        w.writerow([
            tech.timestamp.isoformat(),
            tech.ticker, final_signal, tech.signal,
            f"{tech.price:.2f}", f"{tech.vwap:.2f}",
            f"{tech.price_vs_vwap_pct:.2f}", f"{tech.volume_ratio:.2f}",
            news.label if news else "N/A",
            f"{news.avg_score:.2f}" if news else "0.00",
            reason,
        ])


# ============== الدورة الواحدة ==============
def run_cycle(dry_run: bool = False) -> int:
    """يدور على كل الأسهم ويرسل الإشارات. يعيد عدد الإشارات المُرسلة."""
    logger.info("=" * 60)
    logger.info("بدء دورة تحليل - %s", datetime.now(ET).strftime("%Y-%m-%d %H:%M:%S ET"))
    logger.info("=" * 60)

    sent = 0
    for ticker in config.TICKERS:
        try:
            tech = analyze_ticker(
                ticker=ticker,
                period_days=config.LOOKBACK_DAYS,
                interval=config.INTERVAL,
                volume_spike_mult=config.VOLUME_SPIKE_MULT,
                min_price=config.MIN_PRICE,
                min_avg_volume=config.MIN_AVG_VOLUME,
            )
            if tech is None:
                continue

            news = None
            if config.ENABLE_NEWS_ANALYSIS and tech.signal != "HOLD":
                news = analyze_sentiment(
                    ticker=ticker,
                    lookback_hours=config.NEWS_LOOKBACK_HOURS,
                    max_items=config.MAX_NEWS_PER_TICKER,
                )

            final_signal, reason = combine_signals(tech, news)

            logger.info(
                "[%s] %s | price=$%.2f vwap=$%.2f vol_ratio=%.1fx | news=%s | %s",
                ticker, final_signal, tech.price, tech.vwap, tech.volume_ratio,
                (news.label if news else "N/A"), reason
            )

            append_to_csv(tech, news, final_signal, reason)

            should_send = final_signal in ("BUY", "SELL") or (
                final_signal == "HOLD" and config.SEND_HOLD_SIGNALS
            )
            if should_send:
                msg = format_signal_message(tech, news, combined_signal=final_signal)
                msg += f"\n📌 <i>{reason}</i>"
                if dry_run:
                    print("\n--- DRY RUN ---\n" + msg + "\n----------------\n")
                else:
                    if send_telegram(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, msg):
                        sent += 1
                        time.sleep(1)  # نتجنب rate limit
        except Exception as e:
            logger.exception("Error analyzing %s: %s", ticker, e)

    logger.info("انتهت الدورة. تم إرسال %d إشارة.", sent)
    return sent


# ============== الحلقة الرئيسية ==============
def main_loop(dry_run: bool = False):
    if not dry_run:
        send_startup_message(
            config.TELEGRAM_BOT_TOKEN,
            config.TELEGRAM_CHAT_ID,
            len(config.TICKERS),
        )

    while True:
        now_et = datetime.now(ET)
        if config.ONLY_DURING_MARKET and not is_market_open(now_et):
            logger.info("السوق مغلق (%s ET). إعادة الفحص بعد 5 دقائق...",
                        now_et.strftime("%H:%M"))
            time.sleep(300)
            continue

        try:
            run_cycle(dry_run=dry_run)
        except Exception as e:
            logger.exception("خطأ في الدورة: %s", e)

        sleep_secs = config.RUN_EVERY_MINUTES * 60
        logger.info("ننتظر %d دقيقة قبل الدورة التالية...", config.RUN_EVERY_MINUTES)
        time.sleep(sleep_secs)


def main():
    parser = argparse.ArgumentParser(description="Stock Bot - تحليل المضاربة اليومية")
    parser.add_argument("--once", action="store_true", help="دورة واحدة فقط (بدون حلقة)")
    parser.add_argument("--dry-run", action="store_true", help="بدون إرسال تليجرام")
    args = parser.parse_args()

    setup_logging()

    if args.once:
        run_cycle(dry_run=args.dry_run)
    else:
        main_loop(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
