"""
TradiQ — ML Feature Engineering
Converts raw fundamental + technical data into a flat feature vector for XGBoost.
"""

import numpy as np
from typing import Optional


FEATURE_COLUMNS = [
    # Fundamental
    "pe_ratio", "pb_ratio", "debt_to_equity", "roe", "revenue_growth_yoy",
    "qoq_profit_growth", "promoter_holding", "profit_margins",
    "market_cap_cr", "earnings_growth",
    # Technical
    "rsi_value", "macd_value", "ema20", "ema50", "ema_diff_pct",
    "volume_ratio", "pct_from_52w_low", "bb_width",
    "return_1m", "return_3m", "return_6m", "return_1y",
    # Composite
    "fundamental_score", "technical_score",
]


def build_feature_vector(
    fund: dict,
    tech_result: dict,
    fund_result: dict,
    price_history: dict,
) -> dict:
    """
    Builds a flat feature dict from all analysis outputs.
    Missing values are filled with 0 (XGBoost handles NaN but 0 is safer).
    """
    raw_tech  = tech_result.get("raw", {})
    ema20     = raw_tech.get("ema20", 0)
    ema50     = raw_tech.get("ema50", 1)   # avoid div by zero
    ema_diff  = ((ema20 - ema50) / ema50 * 100) if ema50 else 0

    features = {
        # Fundamentals
        "pe_ratio":             _safe(fund.get("pe_ratio")),
        "pb_ratio":             _safe(fund.get("pb_ratio")),
        "debt_to_equity":       _safe(fund.get("debt_to_equity")),
        "roe":                  _safe(fund.get("roe")),
        "revenue_growth_yoy":   _safe(fund.get("revenue_growth_yoy")),
        "qoq_profit_growth":    _safe(fund.get("qoq_profit_growth")),
        "promoter_holding":     _safe(fund.get("promoter_holding")),
        "profit_margins":       _safe(fund.get("profit_margins")),
        "market_cap_cr":        _safe(fund.get("market_cap_cr")),
        "earnings_growth":      _safe(fund.get("earnings_growth")),

        # Technicals
        "rsi_value":            _safe(raw_tech.get("rsi_value")),
        "macd_value":           _safe(raw_tech.get("macd_value")),
        "ema20":                _safe(ema20),
        "ema50":                _safe(ema50),
        "ema_diff_pct":         _safe(ema_diff),
        "volume_ratio":         _safe(raw_tech.get("volume_ratio")),
        "pct_from_52w_low":     _safe(raw_tech.get("pct_from_52w_low")),
        "bb_width":             _safe(raw_tech.get("bb_width")),
        "return_1m":            _safe(price_history.get("return_1m")),
        "return_3m":            _safe(price_history.get("return_3m")),
        "return_6m":            _safe(price_history.get("return_6m")),
        "return_1y":            _safe(price_history.get("return_1y")),

        # Composite
        "fundamental_score":    _safe(fund_result.get("score")),
        "technical_score":      _safe(tech_result.get("score")),
    }

    return features


def _safe(val, default: float = 0.0) -> float:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def features_to_array(feature_dict: dict) -> np.ndarray:
    """Convert feature dict to numpy array in consistent column order."""
    return np.array([feature_dict.get(col, 0.0) for col in FEATURE_COLUMNS], dtype=np.float32)
