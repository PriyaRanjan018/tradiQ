"""
TradiQ — Stage 1: Universe Filter
Narrows down 5000+ stocks to ~500–800 investable candidates.
Filters: price range, market cap, daily volume, data quality.
"""

import pandas as pd
import logging
from typing import Optional
from config.settings import (
    PRICE_MIN, PRICE_MAX,
    MIN_MARKET_CAP_CR, MIN_AVG_DAILY_VOLUME,
)

logger = logging.getLogger(__name__)


def apply_filters(
    universe_df:       pd.DataFrame,
    ohlcv_data:        dict,          # ticker → OHLCV DataFrame
    fundamentals_data: dict,          # ticker → fundamentals dict
    price_min:  Optional[float] = None,   # override PRICE_MIN from settings
    price_max:  Optional[float] = None,   # override PRICE_MAX from settings (None = no upper limit)
    sector:     Optional[str]   = None,   # restrict to one sector
) -> pd.DataFrame:
    """
    Apply all Stage 1 filters to the universe.

    price_min / price_max / sector override the global settings.py values when provided.

    Returns:
        Filtered DataFrame with columns: current_price, market_cap_cr, avg_volume_20d
    """
    results = []

    for _, row in universe_df.iterrows():
        ticker = row["yf_ticker"]

        ohlcv = ohlcv_data.get(ticker)
        fund  = fundamentals_data.get(ticker, {})

        # ── Skip if no price data ─────────────────────────────────────────────
        if ohlcv is None or ohlcv.empty:
            continue

        current_price = float(ohlcv["Close"].iloc[-1])

        # ── Filter 1: Price range (use override or global settings) ──────────
        p_min = price_min if price_min is not None else PRICE_MIN
        p_max = price_max if price_max is not None else PRICE_MAX
        if not (p_min <= current_price <= p_max):
            continue

        # ── Filter 2: Market Cap > ₹50 Crore ─────────────────────────────────
        market_cap_cr = fund.get("market_cap_cr")
        if market_cap_cr is not None and market_cap_cr < MIN_MARKET_CAP_CR:
            continue

        # ── Filter 3: Avg Daily Volume > 5,000 ───────────────────────────────
        avg_vol = float(ohlcv["Volume"].tail(20).mean())
        if avg_vol < 5000:
            continue

        # ── Filter 4: Data quality — at least 30 trading days ─────────────────
        if len(ohlcv) < 30:
            continue

        # ── Filter 5: No error in fundamentals ───────────────────────────────
        if "error" in fund:
            continue

        # ── Filter 6: Sector restriction (optional) ───────────────────────────
        if sector and sector != "ALL":
            stock_sector = fund.get("sector", "")
            if stock_sector.lower() != sector.lower():
                continue

        results.append({
            **row.to_dict(),
            "current_price":   round(current_price, 2),
            "market_cap_cr":   market_cap_cr,
            "avg_volume_20d":  round(avg_vol, 0),
        })

    filtered_df = pd.DataFrame(results).reset_index(drop=True)
    logger.info(
        f"🔍 Filter result: {len(universe_df)} → {len(filtered_df)} stocks passed"
    )
    return filtered_df
