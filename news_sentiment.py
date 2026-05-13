"""
وحدة تحليل الأخبار والمشاعر
==========================
- يجلب آخر الأخبار من Yahoo Finance لكل سهم
- يحلل المشاعر باستخدام VADER (مكتبة مجانية مدمجة)
- يعيد score بين -1 (سلبي جداً) و +1 (إيجابي جداً)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

_analyzer = SentimentIntensityAnalyzer()


@dataclass
class NewsItem:
    title: str
    publisher: str
    link: str
    published: datetime
    score: float        # compound score من VADER

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "publisher": self.publisher,
            "link": self.link,
            "published": self.published.isoformat(),
            "score": round(self.score, 3),
        }


@dataclass
class NewsSentiment:
    ticker: str
    avg_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    items: List[NewsItem] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.avg_score >= 0.20:
            return "BULLISH"
        elif self.avg_score <= -0.20:
            return "BEARISH"
        return "NEUTRAL"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "avg_score": round(self.avg_score, 3),
            "label": self.label,
            "bullish": self.bullish_count,
            "bearish": self.bearish_count,
            "neutral": self.neutral_count,
            "items": [i.to_dict() for i in self.items],
        }


def _parse_publish_time(raw) -> Optional[datetime]:
    """yfinance يعيد التاريخ أحياناً كـ timestamp وأحياناً كنص"""
    try:
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(raw, tz=timezone.utc)
        if isinstance(raw, str):
            # ISO format
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                pass
    except Exception:
        return None
    return None


def fetch_news(ticker: str, lookback_hours: int = 12, max_items: int = 5) -> List[NewsItem]:
    """يجلب آخر الأخبار من Yahoo Finance"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    items: List[NewsItem] = []

    try:
        raw_news = yf.Ticker(ticker).news or []
    except Exception as e:
        logger.warning("Failed to fetch news for %s: %s", ticker, e)
        return items

    for entry in raw_news[: max_items * 3]:  # نأخذ أكثر لنفلتر حسب الوقت
        # yfinance قد يضع البيانات تحت "content" أو مباشرة
        content = entry.get("content") or entry
        title = content.get("title") or entry.get("title") or ""
        if not title:
            continue

        publisher = (
            content.get("provider", {}).get("displayName")
            if isinstance(content.get("provider"), dict)
            else content.get("publisher") or entry.get("publisher") or "Unknown"
        )

        link = (
            content.get("canonicalUrl", {}).get("url")
            if isinstance(content.get("canonicalUrl"), dict)
            else content.get("link") or entry.get("link") or ""
        )

        pub_raw = (
            content.get("pubDate")
            or content.get("displayTime")
            or entry.get("providerPublishTime")
            or entry.get("pubDate")
        )
        published = _parse_publish_time(pub_raw) or datetime.now(timezone.utc)

        if published < cutoff:
            continue

        score = _analyzer.polarity_scores(title)["compound"]

        items.append(NewsItem(
            title=title,
            publisher=str(publisher),
            link=str(link),
            published=published,
            score=score,
        ))

        if len(items) >= max_items:
            break

    return items


def analyze_sentiment(ticker: str, lookback_hours: int = 12, max_items: int = 5) -> NewsSentiment:
    """يجمع كل أخبار السهم ويعطي توصيف عام"""
    items = fetch_news(ticker, lookback_hours, max_items)
    if not items:
        return NewsSentiment(ticker=ticker, avg_score=0.0,
                             bullish_count=0, bearish_count=0, neutral_count=0,
                             items=[])

    scores = [i.score for i in items]
    avg = sum(scores) / len(scores)
    bullish = sum(1 for s in scores if s >= 0.20)
    bearish = sum(1 for s in scores if s <= -0.20)
    neutral = len(scores) - bullish - bearish

    return NewsSentiment(
        ticker=ticker,
        avg_score=avg,
        bullish_count=bullish,
        bearish_count=bearish,
        neutral_count=neutral,
        items=items,
    )
