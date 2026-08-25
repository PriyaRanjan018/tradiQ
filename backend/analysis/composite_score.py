"""
TradiQ — Composite Score + Target Price Calculator
Combines fundamental (0–50) + technical (0–50) = rule score (0–100).
Also computes price target based on PE expansion and momentum.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# PE expansion multiplier for target price calculation
PE_EXPANSION_FACTOR = 1.25     # Assume PE re-rates 25% higher
REVENUE_MULTIPLE_BOOST = 0.03  # Each % of revenue growth adds 3% to target


def compute_composite_score(
    fundamental_score: float,
    technical_score: float,
) -> float:
    """
    Combines fundamental (0–50) and technical (0–50) scores.
    Rule-based score: 0–100.
    """
    return round(fundamental_score + technical_score, 2)


def estimate_target_price(
    current_price: float,
    fund: dict,
    tech_result: dict,
    composite_score: float,
) -> Optional[float]:
    """
    Estimates a 8–9 month target price using:
      1. PE expansion (if undervalued)
      2. Revenue growth multiplier
      3. Technical momentum boost
      4. Score-based confidence multiplier

    This is a heuristic estimate, not a DCF model.
    """
    if not current_price or current_price <= 0:
        return None

    multiplier = 1.0

    # ── Revenue growth contributes to upside ─────────────────────────────────
    rev_growth = fund.get("revenue_growth_yoy")
    if rev_growth and rev_growth > 0:
        multiplier += min(rev_growth * REVENUE_MULTIPLE_BOOST, 0.30)  # cap at 30%

    # ── PE discount/expansion ─────────────────────────────────────────────────
    pe = fund.get("pe_ratio")
    forward_pe = fund.get("forward_pe")
    if pe and forward_pe and forward_pe < pe:
        multiplier += 0.08   # Forward earnings expansion = +8%

    # ── Technical score boost (max +15% from perfect technicals) ─────────────
    tech_score = tech_result.get("score", 0)
    multiplier += (tech_score / 50) * 0.15

    # ── Bollinger breakout premium ────────────────────────────────────────────
    if tech_result.get("signals", {}).get("bollinger_squeeze"):
        multiplier += 0.10

    # ── Overall confidence scale ──────────────────────────────────────────────
    # Score 80–100 = high confidence = minimal haircut
    # Score 60–80 = medium = moderate haircut
    confidence_factor = composite_score / 100
    multiplier = 1 + (multiplier - 1) * confidence_factor

    target = round(current_price * multiplier, 2)
    return target


def rank_stocks(candidates: list[dict]) -> list[dict]:
    """
    Sort candidates by AI score (descending), then composite score.
    Returns the ranked list with rank field added.
    """
    sorted_list = sorted(
        candidates,
        key=lambda x: (x.get("ai_score", 0), x.get("composite_score", 0)),
        reverse=True,
    )
    for i, stock in enumerate(sorted_list):
        stock["rank"] = i + 1
    return sorted_list
