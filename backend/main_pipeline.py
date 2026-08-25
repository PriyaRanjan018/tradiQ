"""
TradiQ — Main Analysis Pipeline
Orchestrates all stages: Fetch Price → Pre-Filter → Fetch Fundamentals → Score → Rank → Generate Reasons
Optimized for high-speed multi-threaded execution.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fetcher.stock_list      import get_full_universe
from fetcher.price_data      import fetch_bulk_ohlcv, get_52w_stats, get_price_history_summary
from fetcher.fundamentals    import fetch_yfinance_fundamentals, fetch_bulk_fundamentals

from analysis.filters        import apply_filters
from analysis.technical      import compute_technical_score
from analysis.fundamental    import compute_fundamental_score
from analysis.composite_score import compute_composite_score, estimate_target_price, rank_stocks
from analysis.reason_generator import generate_recommendation_reason

from ml.feature_engineering  import build_feature_vector
from ml.predict              import predict_ai_score

from config.settings         import (
    TOP_N_PICKS, AI_SCORE_THRESHOLD,
    PRICE_MIN, PRICE_MAX,
)

logger = logging.getLogger(__name__)


@dataclass
class ScanFilters:
    price_min:  float = PRICE_MIN
    price_max:  float = PRICE_MAX
    exchange:   str   = "ALL"
    min_score:  float = AI_SCORE_THRESHOLD
    sector:     str   = "ALL"
    top_n:      int   = TOP_N_PICKS


def run_pipeline(
    filters:         Optional[ScanFilters] = None,
    limit:           Optional[int]         = None,
    symbols:         Optional[list[str]]   = None,
    force_full_scan: bool                  = False,
) -> list[dict]:
    """
    Full end-to-end pipeline. Returns list of top N stock recommendations.
    If candidate_pool.json exists, filters from the pre-computed 500 candidate stocks instantly!
    """
    if filters is None:
        filters = ScanFilters()

    start_time = time.time()
    run_date   = datetime.now().strftime("%Y-%m-%d %H:%M")
    logger.info(f"🚀 TradiQ pipeline started — {run_date}")

    # Fast path: Check if candidate pool exists and we are not running single symbol/full scan
    if not symbols and not force_full_scan:
        pool_data = load_candidate_pool()
        if pool_data and pool_data.get("candidates"):
            candidates = pool_data["candidates"]
            logger.info(f"⚡ Fast-path active: Filtering from pre-computed pool of {len(candidates)} candidates")
            
            filtered = []
            for c in candidates:
                # Apply price filter
                if c["current_price"] < filters.price_min:
                    continue
                if filters.price_max < 99999 and c["current_price"] > filters.price_max:
                    continue
                # Apply exchange filter
                if filters.exchange != "ALL" and c["exchange"] != filters.exchange:
                    continue
                # Apply min score filter
                if c["ai_score"] < filters.min_score:
                    continue
                # Apply sector filter
                if filters.sector != "ALL" and c.get("sector") != filters.sector:
                    continue
                filtered.append(c)

            ranked = rank_stocks(filtered)
            top_picks = ranked[: filters.top_n]
            for i, pick in enumerate(top_picks, start=1):
                pick["rank"] = i
                
            elapsed = round(time.time() - start_time, 2)
            logger.info(f"⚡ Fast-path complete in {elapsed}s — {len(top_picks)} picks returned from candidate pool!")
            return top_picks

    # ── STAGE 0: Fetch stock universe ──────────────────────────────────────────
    logger.info("📋 Stage 0: Fetching stock universe...")
    universe = get_full_universe()

    if symbols:
        universe = universe[universe["symbol"].isin(symbols)]
    else:
        if filters.exchange != "ALL":
            universe = universe[universe["exchange"] == filters.exchange]

        # Safe Fallback: If no candidate pool exists yet and no explicit limit is provided,
        # cap at 500 stocks to prevent live requests from timing out or hitting rate limits.
        if limit:
            universe = universe.head(limit)
        elif not load_candidate_pool():
            logger.info("⚠️  Candidate pool missing — capping live fallback scan to Top 500 stocks for speed")
            universe = universe.head(500)

    logger.info(f"   Universe size: {len(universe)} stocks")
    tickers = universe["yf_ticker"].tolist()

    # ── STAGE 1: Fast Batch Price Download ────────────────────────────────────
    logger.info("📥 Stage 1: Fetching OHLCV price data...")
    ohlcv_data = fetch_bulk_ohlcv(tickers)
    logger.info(f"   Price data available for {len(ohlcv_data)} stocks")

    # ── STAGE 2: Pre-filter by price & volume (Narrows universe) ─────────────
    logger.info("🔍 Stage 2: Pre-filtering stocks by price & volume...")
    # First pass filters without fundamentals to quickly drop unpromising stocks
    pre_filtered_df = apply_filters(
        universe, ohlcv_data, {},
        price_min=filters.price_min,
        price_max=filters.price_max if filters.price_max < 99999 else None,
        sector=filters.sector if filters.sector != "ALL" else None,
    )
    logger.info(f"   Stocks passing price/volume pre-filter: {len(pre_filtered_df)}")

    # ── STAGE 3: Fetch Fundamentals ONLY for candidate stocks ─────────────────
    logger.info("📊 Stage 3: Fetching fundamentals for candidate stocks...")
    logger.info("📊 Stage 3: Parallel fetching fundamentals for candidate stocks...")
    candidate_tickers = pre_filtered_df["yf_ticker"].tolist()
    fundamentals_data = fetch_bulk_fundamentals(candidate_tickers, max_workers=20)
    logger.info(f"   Fundamentals fetched for {len(fundamentals_data)} candidate stocks")

    # Re-apply full filter with fundamentals
    filtered_df = apply_filters(
        pre_filtered_df, ohlcv_data, fundamentals_data,
        price_min=filters.price_min,
        price_max=filters.price_max if filters.price_max < 99999 else None,
        sector=filters.sector if filters.sector != "ALL" else None,
    )

    # ── STAGE 4: Score each stock ─────────────────────────────────────────────
    logger.info("⚙️  Stage 4: Scoring candidate stocks...")
    candidates = []

    for _, row in filtered_df.iterrows():
        ticker  = row["yf_ticker"]
        ohlcv   = ohlcv_data.get(ticker)
        fund    = fundamentals_data.get(ticker, {})

        tech_result  = compute_technical_score(ohlcv)
        fund_result  = compute_fundamental_score(fund)
        composite    = compute_composite_score(fund_result["score"], tech_result["score"])

        price_history = get_price_history_summary(ohlcv) if ohlcv is not None else {}
        week_stats    = get_52w_stats(ohlcv)             if ohlcv is not None else {}
        current_price = row.get("current_price") or fund.get("current_price") or float(ohlcv["Close"].iloc[-1])

        features  = build_feature_vector(fund, tech_result, fund_result, price_history)
        ai_score  = predict_ai_score(features, composite)

        if ai_score < filters.min_score:
            continue

        target_price = estimate_target_price(current_price, fund, tech_result, composite)

        reasons = generate_recommendation_reason(
            company_name  = fund.get("company_name", row["name"]),
            price_history = price_history,
            week_stats    = week_stats,
            fund          = fund,
            tech_result   = tech_result,
            fund_result   = fund_result,
            ai_score      = ai_score,
            current_price = current_price,
            target_price  = target_price,
        )

        candidates.append({
            "ticker":          ticker,
            "symbol":          row["symbol"],
            "name":            fund.get("company_name", row["name"]),
            "exchange":        row["exchange"],
            "sector":          fund.get("sector", "Industrials"),
            "industry":        fund.get("industry", "General"),
            "current_price":   round(current_price, 2),
            "target_price":    round(target_price, 2),
            "low_52w":         week_stats.get("low_52w"),
            "high_52w":        week_stats.get("high_52w"),
            "ai_score":           round(ai_score, 1),
            "composite_score":    round(composite, 1),
            "fundamental_score":  round(fund_result["score"], 1),
            "technical_score":    round(tech_result["score"], 1),
            "tech_signals":    tech_result["signals"],
            "why":             reasons,
            "run_date":        run_date,
        })

    # ── STAGE 5: Rank & select top N ──────────────────────────────────────────
    logger.info(f"🏆 Stage 5: Ranking and selecting top {filters.top_n}...")
    ranked    = rank_stocks(candidates)
    top_picks = ranked[: filters.top_n]

    for i, pick in enumerate(top_picks, start=1):
        pick["rank"] = i

    elapsed = round(time.time() - start_time, 1)
    logger.info(f"✅ Pipeline complete in {elapsed}s — {len(top_picks)} picks ready")
    return top_picks


CANDIDATE_POOL_PATH = "data/candidate_pool.json"

def build_candidate_pool(top_n: int = 500) -> dict:
    """
    Overnight / Pre-compute job:
    Scans full ~7,200 stock universe slowly, scores all stocks,
    and caches top 500 candidates into data/candidate_pool.json.
    """
    logger.info("🌙 Running overnight Candidate Pool Build (Top 500)...")
    start_time = time.time()
    
    # Run full pipeline with no price/score restrictions to find top 500
    filters = ScanFilters(
        price_min=1,
        price_max=99999,
        exchange="ALL",
        min_score=0,
        sector="ALL",
        top_n=top_n,
    )
    
    # Execute full scan
    candidates = run_pipeline(filters=filters)
    
    pool_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_candidates": len(candidates),
        "candidates": candidates
    }
    
    import json, os
    os.makedirs("data", exist_ok=True)
    with open(CANDIDATE_POOL_PATH, "w") as f:
        json.dump(pool_data, f, indent=2)
        
    elapsed = round(time.time() - start_time, 1)
    logger.info(f"🎉 Candidate Pool successfully built and saved: {len(candidates)} stocks in {elapsed}s")
    return pool_data


def load_candidate_pool() -> Optional[dict]:
    """Load pre-computed candidate pool from disk if present."""
    import os, json
    if not os.path.exists(CANDIDATE_POOL_PATH):
        return None
    try:
        with open(CANDIDATE_POOL_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading candidate pool: {e}")
        return None

