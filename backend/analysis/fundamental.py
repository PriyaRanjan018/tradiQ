"""
TradiQ — Stage 2: Fundamental Analysis Scorer
Scores each stock on 6 fundamental dimensions (0–50 total).
"""

import logging
from config.settings import (
    FUNDAMENTAL_WEIGHTS,
    REVENUE_GROWTH_GOOD, REVENUE_GROWTH_OK,
    PROFIT_GROWTH_GOOD, PROFIT_GROWTH_OK,
    PE_DISCOUNT_NEEDED,
    MAX_DEBT_TO_EQUITY, MAX_DE_HALF,
    ROE_GOOD, ROE_OK,
    PROMOTER_HOLDING_GOOD, PROMOTER_HOLDING_OK,
)
from fetcher.fundamentals import get_sector_pe_averages

logger = logging.getLogger(__name__)

SECTOR_PE = get_sector_pe_averages()


def score_revenue_growth(growth_pct) -> float:
    """Revenue growth YoY"""
    if growth_pct is None:
        return 0
    w = FUNDAMENTAL_WEIGHTS["revenue_growth_yoy"]
    if growth_pct >= REVENUE_GROWTH_GOOD:
        return float(w)
    if growth_pct >= REVENUE_GROWTH_OK:
        return float(w) * 0.5
    return 0.0


def score_profit_growth(growth_pct) -> float:
    """Profit growth QoQ"""
    if growth_pct is None:
        return 0
    w = FUNDAMENTAL_WEIGHTS["profit_growth_qoq"]
    if growth_pct >= PROFIT_GROWTH_GOOD:
        return float(w)
    if growth_pct >= PROFIT_GROWTH_OK:
        return float(w) * 0.5
    return 0.0


def score_pe_ratio(pe_ratio, sector: str) -> float:
    """PE ratio vs sector average"""
    if pe_ratio is None or pe_ratio <= 0:
        return 0
    sector_avg = SECTOR_PE.get(sector, SECTOR_PE["Unknown"])
    w = FUNDAMENTAL_WEIGHTS["pe_vs_sector"]
    discount_pct = (sector_avg - pe_ratio) / sector_avg * 100
    if discount_pct >= PE_DISCOUNT_NEEDED:
        return float(w)
    if discount_pct >= PE_DISCOUNT_NEEDED / 2:
        return float(w) * 0.5
    return 0.0


def score_debt_to_equity(de_ratio) -> float:
    """Debt to equity — lower is better"""
    if de_ratio is None:
        return FUNDAMENTAL_WEIGHTS["debt_to_equity"] * 0.5  # neutral if unknown
    w = FUNDAMENTAL_WEIGHTS["debt_to_equity"]
    if de_ratio <= MAX_DEBT_TO_EQUITY:
        return float(w)
    if de_ratio <= MAX_DE_HALF:
        return float(w) * 0.5
    return 0.0


def score_roe(roe_pct) -> float:
    """Return on Equity"""
    if roe_pct is None:
        return 0
    w = FUNDAMENTAL_WEIGHTS["roe"]
    if roe_pct >= ROE_GOOD:
        return float(w)
    if roe_pct >= ROE_OK:
        return float(w) * 0.5
    return 0.0


def score_promoter_holding(holding_pct) -> float:
    """Promoter shareholding"""
    if holding_pct is None:
        return 0
    w = FUNDAMENTAL_WEIGHTS["promoter_holding"]
    if holding_pct >= PROMOTER_HOLDING_GOOD:
        return float(w)
    if holding_pct >= PROMOTER_HOLDING_OK:
        return float(w) * 0.5
    return 0.0


def compute_fundamental_score(fund: dict) -> dict:
    """
    Compute full fundamental score for a stock.

    Returns:
    {
        "score": float (0–50),
        "breakdown": {
            "revenue_growth": ..., "profit_growth": ..., "pe_vs_sector": ...,
            "debt_to_equity": ..., "roe": ..., "promoter_holding": ...
        },
        "data": { all raw fundamental values }
    }
    """
    if not fund or "error" in fund:
        return {"score": 0.0, "breakdown": {}, "data": fund}

    sector = fund.get("sector", "Unknown")

    s_rev  = score_revenue_growth(fund.get("revenue_growth_yoy"))
    s_prof = score_profit_growth(fund.get("qoq_profit_growth") or fund.get("earnings_growth"))
    s_pe   = score_pe_ratio(fund.get("pe_ratio"), sector)
    s_de   = score_debt_to_equity(fund.get("debt_to_equity"))
    s_roe  = score_roe(fund.get("roe"))
    s_prom = score_promoter_holding(fund.get("promoter_holding"))

    total = s_rev + s_prof + s_pe + s_de + s_roe + s_prom

    return {
        "score": round(total, 2),
        "breakdown": {
            "revenue_growth": round(s_rev, 2),
            "profit_growth":  round(s_prof, 2),
            "pe_vs_sector":   round(s_pe, 2),
            "debt_to_equity": round(s_de, 2),
            "roe":            round(s_roe, 2),
            "promoter_holding": round(s_prom, 2),
        },
        "data": fund,
    }
