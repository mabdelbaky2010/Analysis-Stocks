"""
وحدة التحليل الفني
==================
- VWAP (Volume Weighted Average Price) محسوب من بيانات اليوم
- اكتشاف قفزات الحجم (Volume Spike) مقارنة بالمتوسط
- إشارات BUY / SELL بناءً على تقاطع السعر مع VWAP + قفزة حجم
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)


@dataclass
class TechnicalSignal:
    ticker: str
    price: float
    vwap: float
    volume: int
    avg_volume: float
    volume_ratio: float
    price_vs_vwap_pct: float
    signal: str          # "BUY" | "SELL" | "HOLD"
    reason: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "price": round(self.price, 2),
            "vwap": round(self.vwap, 2),
            "volume": int(self.volume),
            "avg_volume": int(self.avg_volume),
            "volume_ratio": round(self.volume_ratio, 2),
            "price_vs_vwap_pct": round(self.price_vs_vwap_pct, 2),
            "signal": self.signal,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat(),
        }


def fetch_intraday(ticker: str, period_days: int = 2, interval: str = "15m") -> Optional[pd.DataFrame]:
    """جلب بيانات السهم خلال اليوم (15 دقيقة)"""
    try:
        df = yf.download(
            ticker,
            period=f"{period_days}d",
            interval=interval,
            progress=False,
            auto_adjust=False,
            prepost=False,
            threads=False,
        )
        if df is None or df.empty:
            return None
        # يفلتن أعمدة MultiIndex إذا وُجدت
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df
    except Exception as e:
        logger.warning("Failed to fetch %s: %s", ticker, e)
        return None


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """حساب VWAP لليوم الحالي فقط"""
    df = df.copy()
    # ابقِ فقط شموع اليوم الأخير
    last_date = df.index[-1].date()
    today_mask = df.index.date == last_date
    today = df.loc[today_mask].copy()
    if today.empty:
        return pd.Series(dtype=float)

    typical_price = (today["High"] + today["Low"] + today["Close"]) / 3.0
    cum_pv = (typical_price * today["Volume"]).cumsum()
    cum_vol = today["Volume"].cumsum().replace(0, np.nan)
    vwap = cum_pv / cum_vol
    return vwap


def analyze_ticker(
    ticker: str,
    period_days: int = 2,
    interval: str = "15m",
    volume_spike_mult: float = 1.8,
    min_price: float = 5.0,
    min_avg_volume: float = 500_000,
) -> Optional[TechnicalSignal]:
    """يولّد إشارة فنية واحدة لسهم معين"""
    df = fetch_intraday(ticker, period_days, interval)
    if df is None or len(df) < 25:
        return None

    last = df.iloc[-1]
    price = float(last["Close"])
    volume = int(last["Volume"])

    if price < min_price:
        return None

    avg_volume_20 = float(df["Volume"].tail(20).mean())
    if avg_volume_20 < min_avg_volume:
        return None

    volume_ratio = volume / avg_volume_20 if avg_volume_20 else 0.0

    vwap_series = compute_vwap(df)
    if vwap_series.empty or pd.isna(vwap_series.iloc[-1]):
        return None
    vwap = float(vwap_series.iloc[-1])

    price_vs_vwap_pct = ((price - vwap) / vwap) * 100.0

    # شمعة سابقة لتحديد التقاطع
    prev_close = float(df["Close"].iloc[-2])
    today_mask = df.index.date == df.index[-1].date()
    today_vwap = vwap_series.reindex(df.index[today_mask]).dropna()
    if len(today_vwap) >= 2:
        prev_vwap = float(today_vwap.iloc[-2])
    else:
        prev_vwap = vwap

    crossed_up   = prev_close <= prev_vwap and price > vwap
    crossed_down = prev_close >= prev_vwap and price < vwap

    signal = "HOLD"
    reason_parts = []

    if volume_ratio >= volume_spike_mult:
        reason_parts.append(f"Volume {volume_ratio:.1f}x avg")
        if crossed_up and price_vs_vwap_pct > 0:
            signal = "BUY"
            reason_parts.append(f"Price crossed ABOVE VWAP (+{price_vs_vwap_pct:.2f}%)")
        elif crossed_down and price_vs_vwap_pct < 0:
            signal = "SELL"
            reason_parts.append(f"Price crossed BELOW VWAP ({price_vs_vwap_pct:.2f}%)")
        elif price_vs_vwap_pct > 0.5:
            signal = "BUY"
            reason_parts.append(f"Strong above VWAP (+{price_vs_vwap_pct:.2f}%)")
        elif price_vs_vwap_pct < -0.5:
            signal = "SELL"
            reason_parts.append(f"Strong below VWAP ({price_vs_vwap_pct:.2f}%)")
    else:
        reason_parts.append(f"Volume only {volume_ratio:.1f}x avg (no spike)")

    return TechnicalSignal(
        ticker=ticker,
        price=price,
        vwap=vwap,
        volume=volume,
        avg_volume=avg_volume_20,
        volume_ratio=volume_ratio,
        price_vs_vwap_pct=price_vs_vwap_pct,
        signal=signal,
        reason=" | ".join(reason_parts),
        timestamp=df.index[-1].to_pydatetime(),
    )
