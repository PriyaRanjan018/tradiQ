"""
TradiQ — Batched Overnight Stock Scanner
Scans all 7,200+ stocks in safe batches of 100, with a small delay between
each batch to avoid Yahoo Finance rate limits.
Called by the nightly scheduler (Mon-Sat 2:00 AM IST) and Saturday deep scan.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("tradiq.batch_scanner")

CANDIDATE_POOL_PATH = "data/candidate_pool.json"
BATCH_SIZE          = 100    # stocks per batch
BATCH_DELAY_S       = 3      # seconds to wait between batches (rate-limit safety)


def run_batched_scan(top_n: int = 500) -> dict:
    """
    Scan the FULL stock universe (~7,200 stocks) in batches of 100.
    After all batches are done, pick the top `top_n` by AI score and
    write them to candidate_pool.json.

    Returns the pool dict (same shape as build_candidate_pool used to return).
    """
    from fetcher.stock_list import get_full_universe
    from fetcher.price_data import fetch_bulk_ohlcv, get_52w_stats, get_price_history_summary
    from fetcher.fundamentals import fetch_bulk_fundamentals
    from analysis.filters import apply_filters
    from analysis.technical import compute_technical_score
    from analysis.fundamental import compute_fundamental_score
    from analysis.composite_score import compute_composite_score, estimate_target_price, rank_stocks
    from analysis.reason_generator import generate_recommendation_reason
    from ml.feature_engineering import build_feature_vector
    from ml.predict import predict_ai_score

    logger.info("🌙 Batched overnight scan starting...")
    overall_start = time.time()
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── 1. Fetch full universe ──────────────────────────────────────────────────
    universe = get_full_universe()
    all_rows = list(universe.itertuples(index=False))
    total    = len(all_rows)
    logger.info(f"📋 Universe: {total} stocks — running in batches of {BATCH_SIZE}")

    all_candidates: list[dict] = []

    # ── 2. Process batch by batch ───────────────────────────────────────────────
    for batch_num, start_idx in enumerate(range(0, total, BATCH_SIZE), start=1):
        batch_rows = all_rows[start_idx : start_idx + BATCH_SIZE]
        tickers    = [r.yf_ticker for r in batch_rows]

        logger.info(
            f"🔄 Batch {batch_num}/{(total + BATCH_SIZE - 1) // BATCH_SIZE} "
            f"— stocks {start_idx + 1}–{min(start_idx + BATCH_SIZE, total)}"
        )

        try:
            # Fetch price data for this batch
            import pandas as pd
            batch_df   = pd.DataFrame([r._asdict() for r in batch_rows])
            ohlcv_data = fetch_bulk_ohlcv(tickers)

            if not ohlcv_data:
                logger.warning(f"  ⚠️  No price data for batch {batch_num}, skipping")
                time.sleep(BATCH_DELAY_S)
                continue

            # Pre-filter by price & volume (price_min=1, no max cap for pool build)
            pre_filtered = apply_filters(batch_df, ohlcv_data, {}, price_min=1)

            if pre_filtered.empty:
                time.sleep(BATCH_DELAY_S)
                continue

            # Fetch fundamentals for surviving stocks
            candidate_tickers = pre_filtered["yf_ticker"].tolist()
            fundamentals_data = fetch_bulk_fundamentals(candidate_tickers, max_workers=10)

            # Score each stock in the batch
            for _, row in pre_filtered.iterrows():
                ticker = row["yf_ticker"]
                ohlcv  = ohlcv_data.get(ticker)
                fund   = fundamentals_data.get(ticker, {})

                try:
                    tech_result   = compute_technical_score(ohlcv)
                    fund_result   = compute_fundamental_score(fund)
                    composite     = compute_composite_score(fund_result["score"], tech_result["score"])
                    price_history = get_price_history_summary(ohlcv) if ohlcv is not None else {}
                    week_stats    = get_52w_stats(ohlcv)             if ohlcv is not None else {}

                    current_price = (
                        row.get("current_price")
                        or fund.get("current_price")
                        or (float(ohlcv["Close"].iloc[-1]) if ohlcv is not None and not ohlcv.empty else None)
                    )
                    if current_price is None:
                        continue

                    features = build_feature_vector(fund, tech_result, fund_result, price_history)
                    ai_score = predict_ai_score(features, composite)

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

                    all_candidates.append({
                        "ticker":             ticker,
                        "symbol":             row["symbol"],
                        "name":               fund.get("company_name", row["name"]),
                        "exchange":           row["exchange"],
                        "sector":             fund.get("sector", "Industrials"),
                        "industry":           fund.get("industry", "General"),
                        "current_price":      round(current_price, 2),
                        "target_price":       round(target_price, 2),
                        "low_52w":            week_stats.get("low_52w"),
                        "high_52w":           week_stats.get("high_52w"),
                        "ai_score":           round(ai_score, 1),
                        "composite_score":    round(composite, 1),
                        "fundamental_score":  round(fund_result["score"], 1),
                        "technical_score":    round(tech_result["score"], 1),
                        "tech_signals":       tech_result["signals"],
                        "why":                reasons,
                        "run_date":           run_date,
                    })
                except Exception as stock_err:
                    logger.debug(f"  Skipping {ticker}: {stock_err}")

        except Exception as batch_err:
            logger.error(f"  ❌ Batch {batch_num} failed: {batch_err}", exc_info=True)

        # Rate-limit safety pause between batches
        time.sleep(BATCH_DELAY_S)

    # ── 3. Rank all candidates and pick top_n ───────────────────────────────────
    logger.info(f"📊 Total scored candidates: {len(all_candidates)}")
    ranked     = rank_stocks(all_candidates)
    top_pool   = ranked[:top_n]

    for i, pick in enumerate(top_pool, start=1):
        pick["rank"] = i

    # ── 4. Save to disk ─────────────────────────────────────────────────────────
    pool_data = {
        "updated_at":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_candidates": len(top_pool),
        "batch_size":       BATCH_SIZE,
        "total_scanned":    total,
        "candidates":       top_pool,
    }

    os.makedirs("data", exist_ok=True)
    with open(CANDIDATE_POOL_PATH, "w") as f:
        json.dump(pool_data, f, indent=2, default=str)

    elapsed = round((time.time() - overall_start) / 60, 1)
    logger.info(
        f"🎉 Batched scan complete — {len(top_pool)} candidates saved "
        f"(scanned {total} stocks in {elapsed} mins)"
    )
    return pool_data
