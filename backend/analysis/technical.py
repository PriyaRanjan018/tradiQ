"""
TradiQ — Stage 3: Technical Analysis
Computes RSI, MACD, EMA crossover, Volume spike, 52W proximity, Bollinger Bands.
Returns a score (0–50) and individual signal dict for use in "Why" narrative.
"""

import pandas as pd
import numpy as np
import logging
from config.settings import (
    TECHNICAL_WEIGHTS,
    RSI_OVERSOLD_LOW, RSI_OVERSOLD_HIGH,
    VOLUME_SPIKE_MULT, NEAR_52W_LOW_PCT,
    BB_SQUEEZE_WIDTH,
)

logger = logging.getLogger(__name__)


# ── Indicator Computations ────────────────────────────────────────────────────

def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast   = close.ewm(span=fast, adjust=False).mean()
    ema_slow   = close.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram  = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False).mean()


def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2.0):
    sma        = close.rolling(window).mean()
    std        = close.rolling(window).std()
    upper_band = sma + num_std * std
    lower_band = sma - num_std * std
    band_width = (upper_band - lower_band) / sma  # normalized width
    return upper_band, lower_band, band_width


# ── Main Technical Scorer ─────────────────────────────────────────────────────

def compute_technical_score(ohlcv: pd.DataFrame) -> dict:
    """
    Computes all technical indicators and returns:
    {
        "score": float (0–50),
        "signals": {
            "rsi": ..., "macd_crossover": ..., "ema_crossover": ...,
            "volume_spike": ..., "near_52w_low": ..., "bollinger_squeeze": ...
        },
        "raw": {
            "rsi_value": ..., "macd_value": ..., "ema20": ..., "ema50": ...,
            "volume_ratio": ..., "pct_from_52w_low": ..., "bb_width": ...
        }
    }
    """
    if ohlcv is None or ohlcv.empty or len(ohlcv) < 50:
        return {"score": 0.0, "signals": {}, "raw": {}}

    close  = ohlcv["Close"].astype(float)
    volume = ohlcv["Volume"].astype(float)
    high   = ohlcv["High"].astype(float)
    low    = ohlcv["Low"].astype(float)

    # ── RSI ───────────────────────────────────────────────────────────────────
    rsi_series = compute_rsi(close)
    rsi_val    = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0
    rsi_signal = RSI_OVERSOLD_LOW <= rsi_val <= RSI_OVERSOLD_HIGH
    rsi_score  = TECHNICAL_WEIGHTS["rsi"] if rsi_signal else 0

    # ── MACD Crossover ────────────────────────────────────────────────────────
    macd_line, signal_line, histogram = compute_macd(close)
    macd_val   = float(macd_line.iloc[-1])
    sig_val    = float(signal_line.iloc[-1])
    hist_now   = float(histogram.iloc[-1])
    hist_prev  = float(histogram.iloc[-2]) if len(histogram) > 1 else 0.0
    # Bullish crossover: MACD crosses above signal (histogram flips positive)
    macd_crossover = (hist_now > 0) and (hist_prev <= 0)
    # Also count if MACD > signal and rising
    macd_bullish   = macd_val > sig_val and hist_now > hist_prev
    macd_signal    = macd_crossover or macd_bullish
    macd_score     = TECHNICAL_WEIGHTS["macd_crossover"] if macd_signal else 0

    # ── EMA Golden Cross (20 > 50) ────────────────────────────────────────────
    ema20 = compute_ema(close, 20)
    ema50 = compute_ema(close, 50)
    ema20_val = float(ema20.iloc[-1])
    ema50_val = float(ema50.iloc[-1])
    ema_cross_signal = ema20_val > ema50_val
    # Extra: confirm cross happened recently (within 10 days)
    ema_cross_recent = False
    if len(ema20) > 10:
        for i in range(1, min(10, len(ema20))):
            if float(ema20.iloc[-i-1]) <= float(ema50.iloc[-i-1]):
                ema_cross_recent = True
                break
    ema_score = TECHNICAL_WEIGHTS["ema_crossover"] if ema_cross_signal else 0
    if ema_cross_recent:
        ema_score = TECHNICAL_WEIGHTS["ema_crossover"]  # Full score for fresh cross

    # ── Volume Spike ──────────────────────────────────────────────────────────
    avg_vol_20  = float(volume.tail(20).mean())
    latest_vol  = float(volume.iloc[-1])
    vol_ratio   = (latest_vol / avg_vol_20) if avg_vol_20 > 0 else 0
    vol_signal  = vol_ratio >= VOLUME_SPIKE_MULT
    vol_score   = TECHNICAL_WEIGHTS["volume_spike"] if vol_signal else (
        TECHNICAL_WEIGHTS["volume_spike"] // 2 if vol_ratio >= 1.2 else 0
    )

    # ── Near 52-Week Low ──────────────────────────────────────────────────────
    low_52w       = float(low.tail(252).min())
    current_price = float(close.iloc[-1])
    pct_from_low  = (current_price - low_52w) / low_52w if low_52w > 0 else 1.0
    near_52w_signal = pct_from_low <= NEAR_52W_LOW_PCT
    near_52w_score  = TECHNICAL_WEIGHTS["near_52w_low"] if near_52w_signal else (
        TECHNICAL_WEIGHTS["near_52w_low"] // 2 if pct_from_low <= 0.35 else 0
    )

    # ── Bollinger Band Squeeze ────────────────────────────────────────────────
    _, _, bb_width = compute_bollinger_bands(close)
    bb_width_val   = float(bb_width.iloc[-1]) if not bb_width.empty else 0.1
    bb_signal      = bb_width_val <= BB_SQUEEZE_WIDTH
    bb_score       = TECHNICAL_WEIGHTS["bollinger_squeeze"] if bb_signal else (
        TECHNICAL_WEIGHTS["bollinger_squeeze"] // 2 if bb_width_val <= 0.08 else 0
    )

    total_score = rsi_score + macd_score + ema_score + vol_score + near_52w_score + bb_score

    return {
        "score": round(float(total_score), 2),
        "signals": {
            "rsi":              rsi_signal,
            "macd_crossover":   macd_signal,
            "ema_crossover":    ema_cross_signal,
            "volume_spike":     vol_signal,
            "near_52w_low":     near_52w_signal,
            "bollinger_squeeze": bb_signal,
        },
        "raw": {
            "rsi_value":        round(rsi_val, 2),
            "macd_value":       round(macd_val, 4),
            "signal_value":     round(sig_val, 4),
            "ema20":            round(ema20_val, 2),
            "ema50":            round(ema50_val, 2),
            "volume_ratio":     round(vol_ratio, 2),
            "pct_from_52w_low": round(pct_from_low * 100, 2),
            "bb_width":         round(bb_width_val, 4),
            "low_52w":          round(low_52w, 2),
        }
    }
