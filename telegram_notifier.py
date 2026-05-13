"""
وحدة إرسال الإشارات لتليجرام
==========================
"""

from __future__ import annotations
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram(token: str, chat_id: str, message: str, parse_mode: str = "HTML") -> bool:
    """يرسل رسالة لبوت تليجرام. يعيد True إذا نجح."""
    if not token or token.startswith("ضع_") or not chat_id or str(chat_id).startswith("ضع_"):
        logger.error("Telegram token/chat_id غير محددين في config.py")
        print("\n[!] لم يتم إعداد توكن تليجرام بعد. الرسالة التي كانت ستُرسل:\n")
        print(message)
        print()
        return False

    url = TELEGRAM_API.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, data=payload, timeout=15)
        if r.status_code != 200:
            logger.error("Telegram error %s: %s", r.status_code, r.text)
            return False
        return True
    except Exception as e:
        logger.error("Telegram exception: %s", e)
        return False


def format_signal_message(tech_signal, news_sentiment=None, combined_signal: Optional[str] = None) -> str:
    """يبني رسالة تليجرام جميلة لكل إشارة"""
    emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "⚪"}
    sig = combined_signal or tech_signal.signal
    e = emoji.get(sig, "•")

    msg = (
        f"{e} <b>{sig}</b>  |  <b>{tech_signal.ticker}</b>\n"
        f"━━━━━━━━━━━━━━━━━\n"
        f"💵 السعر: <b>${tech_signal.price:.2f}</b>\n"
        f"📊 VWAP: ${tech_signal.vwap:.2f}  ({tech_signal.price_vs_vwap_pct:+.2f}%)\n"
        f"📈 الحجم: {tech_signal.volume:,}  ({tech_signal.volume_ratio:.1f}× المتوسط)\n"
        f"🧮 السبب الفني: {tech_signal.reason}\n"
    )

    if news_sentiment and news_sentiment.items:
        news_emoji = {"BULLISH": "📰🟢", "BEARISH": "📰🔴", "NEUTRAL": "📰⚪"}
        msg += (
            f"\n{news_emoji.get(news_sentiment.label, '📰')} الأخبار: "
            f"<b>{news_sentiment.label}</b>  ({news_sentiment.avg_score:+.2f})\n"
        )
        for item in news_sentiment.items[:3]:
            arrow = "↑" if item.score >= 0.20 else ("↓" if item.score <= -0.20 else "→")
            title_short = item.title[:90] + ("..." if len(item.title) > 90 else "")
            msg += f"  {arrow} <a href=\"{item.link}\">{title_short}</a>\n"

    msg += f"\n🕒 {tech_signal.timestamp.strftime('%Y-%m-%d %H:%M')}"
    return msg


def send_startup_message(token: str, chat_id: str, n_tickers: int) -> None:
    msg = (
        f"🤖 <b>Stock Bot شغّال</b>\n"
        f"📡 يراقب {n_tickers} سهم كل 15 دقيقة\n"
        f"📊 VWAP + Volume Spike + News Sentiment\n"
    )
    send_telegram(token, chat_id, msg)
