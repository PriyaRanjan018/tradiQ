"""
TradiQ — Price Data Fetcher
Fast multi-threaded bulk OHLCV fetcher using yfinance.
Also incorporates nselib fallback.
"""

import os
import pickle
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional
from config.settings import CACHE_DIR, LOOKBACK_DAYS

logger = logging.getLogger(__name__)
PRICE_CACHE_DIR = os.path.join(CACHE_DIR, "prices")


def _cache_path(ticker: str) -> str:
    os.makedirs(PRICE_CACHE_DIR, exist_ok=True)
    safe = ticker.replace(".", "_").replace("/", "_")
    return os.path.join(PRICE_CACHE_DIR, f"{safe}.pkl")


def _is_fresh(path: str, ttl_hours: int = 12) -> bool:
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < timedelta(hours=ttl_hours)


def fetch_ohlcv(ticker: str, period_days: int = LOOKBACK_DAYS) -> Optional[pd.DataFrame]:
    """Fetch single ticker OHLCV (cached)."""
    cache = _cache_path(ticker)
    if _is_fresh(cache):
        try:
            return pickle.load(open(cache, "rb"))
        except Exception:
            pass

    try:
        raw = yf.download(ticker, period="1y", progress=False, auto_adjust=True, threads=False)
        if raw is None or raw.empty or len(raw) < 50:
            return None

        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
        raw["ticker"] = ticker
        raw.index = pd.to_datetime(raw.index)
        raw = raw.dropna()

        if len(raw) < 50:
            return None

        pickle.dump(raw, open(cache, "wb"))
        return raw
    except Exception as e:
        logger.debug(f"Fetch error for {ticker}: {e}")
        return None


def fetch_bulk_ohlcv(
    tickers: list[str],
    period_days: int = LOOKBACK_DAYS,
    batch_size: int = 100,
    delay_ms: int = 150,
) -> dict[str, pd.DataFrame]:
    """
    Fast multi-threaded batch download of OHLCV data for hundreds of tickers.
    Scans in batches of 100 with fallback to individual fetch.
    """
    results = {}
    uncached = []

    # 1. Check local cache first
    for ticker in tickers:
        cache = _cache_path(ticker)
        if _is_fresh(cache):
            try:
                df = pickle.load(open(cache, "rb"))
                if df is not None and not df.empty:
                    results[ticker] = df
                    continue
            except Exception:
                pass
        uncached.append(ticker)

    logger.info(f"  OHLCV Cache: {len(results)} cached, {len(uncached)} to fetch online")

    if not uncached:
        return results

    # 2. Batch download uncached tickers in chunks of batch_size
    for i in range(0, len(uncached), batch_size):
        chunk = uncached[i : i + batch_size]
        logger.info(f"  Downloading batch {i//batch_size + 1}/{(len(uncached)-1)//batch_size + 1} ({len(chunk)} tickers)...")

        try:
            bulk_data = yf.download(
                chunk,
                period="1y",
                group_by="ticker",
                threads=True,
                progress=False,
                auto_adjust=True,
            )

            if bulk_data is not None and not bulk_data.empty:
                # Handle single ticker response vs multi-ticker MultiIndex
                if len(chunk) == 1:
                    ticker = chunk[0]
                    raw = bulk_data.dropna()
                    if len(raw) >= 50:
                        raw["ticker"] = ticker
                        results[ticker] = raw
                        pickle.dump(raw, open(_cache_path(ticker), "wb"))
                else:
                    for ticker in chunk:
                        try:
                            if ticker in bulk_data.columns.levels[0]:
                                raw = bulk_data[ticker].dropna()
                                if len(raw) >= 50 and "Close" in raw.columns:
                                    raw = raw[["Open", "High", "Low", "Close", "Volume"]].copy()
                                    raw["ticker"] = ticker
                                    raw.index = pd.to_datetime(raw.index)
                                    results[ticker] = raw
                                    pickle.dump(raw, open(_cache_path(ticker), "wb"))
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Batch fetch error: {e}")

    logger.info(f"  OHLCV fetch complete: {len(results)}/{len(tickers)} available")
    return results


def get_52w_stats(df: pd.DataFrame) -> dict:
    """Compute 52-week high, low, and current price stats."""
    if df is None or df.empty:
        return {}

    one_year_ago = datetime.now() - timedelta(days=365)
    df_1y = df[df.index >= one_year_ago]
    if df_1y.empty:
        df_1y = df

    high_52w = float(df_1y["High"].max())
    low_52w  = float(df_1y["Low"].min())
    current  = float(df["Close"].iloc[-1])

    pct_from_low  = (current - low_52w) / low_52w * 100 if low_52w > 0 else 0
    pct_from_high = (high_52w - current) / high_52w * 100 if high_52w > 0 else 0

    return {
        "high_52w":          round(high_52w, 2),
        "low_52w":           round(low_52w, 2),
        "current_price":     round(current, 2),
        "pct_from_52w_low":  round(pct_from_low, 2),
        "pct_from_52w_high": round(pct_from_high, 2),
    }


def get_price_history_summary(df: pd.DataFrame) -> dict:
    """Returns recent price performance summary (1M, 3M, 6M, 1Y)."""
    if df is None or df.empty:
        return {}

    now = df.index[-1]
    current_price = float(df["Close"].iloc[-1])

    def pct_change_since(days_ago: int) -> Optional[float]:
        cutoff = now - timedelta(days=days_ago)
        past = df[df.index >= cutoff]
        if past.empty or len(past) < 2:
            return None
        old_price = float(past["Close"].iloc[0])
        return round((current_price - old_price) / old_price * 100, 2) if old_price > 0 else None

    return {
        "return_1m":       pct_change_since(30),
        "return_3m":       pct_change_since(90),
        "return_6m":       pct_change_since(180),
        "return_1y":       pct_change_since(365),
        "avg_volume_20d":  round(float(df["Volume"].tail(20).mean()), 0),
        "current_price":   current_price,
    }
