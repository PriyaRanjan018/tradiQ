"""
TradiQ — FastAPI Routes
All HTTP endpoints for the web dashboard.
"""

import os
import json
import glob
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from api.schemas import StatusResponse
from main_pipeline import run_pipeline, ScanFilters
from config.settings import TOP_N_PICKS, ML_MODEL_PATH, AI_SCORE_THRESHOLD, PRICE_MIN, PRICE_MAX

router = APIRouter()
logger = logging.getLogger(__name__)

REPORTS_DIR = "data/reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

# In-memory pipeline state
_pipeline_state = {
    "running":    False,
    "last_run":   None,
    "last_error": None,
    "last_filters": None,   # what filters the last scan used
}


def _save_report(picks: list[dict], run_date: str):
    """Save a scan report to disk as JSON."""
    safe_date = run_date.replace(" ", "_").replace(":", "-")
    path = os.path.join(REPORTS_DIR, f"report_{safe_date}.json")
    with open(path, "w") as f:
        json.dump(picks, f, indent=2, default=str)
    logger.info(f"Report saved: {path}")
    return path


def _load_latest_report() -> list[dict]:
    """Load the most recently saved report."""
    files = sorted(
        glob.glob(os.path.join(REPORTS_DIR, "report_*.json")), reverse=True
    )
    if not files:
        return []
    with open(files[0]) as f:
        return json.load(f)


def _load_all_reports() -> list[dict]:
    """Load summary of all past reports."""
    files = sorted(
        glob.glob(os.path.join(REPORTS_DIR, "report_*.json")), reverse=True
    )
    summaries = []
    for fpath in files:
        try:
            with open(fpath) as f:
                picks = json.load(f)
            if picks:
                summaries.append({
                    "run_date":    picks[0].get("run_date", "unknown"),
                    "total_picks": len(picks),
                    "top_pick":    picks[0].get("name"),
                    "top_score":   picks[0].get("ai_score"),
                    "scan_filters": picks[0].get("scan_filters", {}),
                })
        except Exception:
            pass
    return summaries


def _run_pipeline_background(filters: ScanFilters):
    """Wrapper to run pipeline in background and save results."""
    global _pipeline_state
    _pipeline_state["running"]      = True
    _pipeline_state["last_filters"] = {
        "price_min": filters.price_min,
        "price_max": filters.price_max,
        "exchange":  filters.exchange,
        "min_score": filters.min_score,
        "sector":    filters.sector,
        "top_n":     filters.top_n,
    }
    try:
        picks    = run_pipeline(filters=filters)
        run_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        _save_report(picks, run_date)
        _pipeline_state["last_run"]   = run_date
        _pipeline_state["last_error"] = None
        logger.info(f"Pipeline complete: {len(picks)} picks saved")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        _pipeline_state["last_error"] = str(e)
    finally:
        _pipeline_state["running"] = False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/api/picks/latest")
async def get_latest_picks():
    """Return the most recent scan's stock picks."""
    picks = _load_latest_report()
    if not picks:
        raise HTTPException(
            status_code=404,
            detail="No scan results yet. Click 'Run Live Scan' to start."
        )
    return picks


@router.get("/api/picks/history")
async def get_picks_history():
    """Return summary of all past scans."""
    return _load_all_reports()


@router.get("/api/picks/date/{run_date}")
async def get_picks_by_date(run_date: str):
    """Return picks for a specific date."""
    path = os.path.join(REPORTS_DIR, f"report_{run_date}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"No report found for {run_date}")
    with open(path) as f:
        return json.load(f)


@router.post("/api/run")
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    # ── Filter query params (all optional — UI sends these) ─────────────────
    price_min:  float = Query(default=PRICE_MIN,          ge=1,       description="Min stock price in ₹"),
    price_max:  float = Query(default=PRICE_MAX,          ge=1,       description="Max stock price in ₹ (99999 = no limit)"),
    exchange:   str   = Query(default="ALL",                           description="Exchange filter: ALL | NSE | BSE"),
    min_score:  float = Query(default=AI_SCORE_THRESHOLD, ge=0, le=100,description="Minimum AI score (0–100)"),
    sector:     str   = Query(default="ALL",                           description="Sector filter or ALL"),
    top_n:      int   = Query(default=TOP_N_PICKS,        ge=1, le=50, description="How many top picks to return"),
):
    """
    Trigger a live market scan with the given filters.

    The pipeline will:
      1. Fetch all NSE + BSE stocks (~5,200)
      2. Apply price / exchange / sector filters
      3. Score each stock (Fundamental + Technical + AI)
      4. Return the top N by AI score

    Results are saved and available via /api/picks/latest.
    """
    if _pipeline_state["running"]:
        return {
            "status": "already_running",
            "message": "A scan is already in progress. Check /api/status for updates."
        }

    filters = ScanFilters(
        price_min = price_min,
        price_max = price_max,
        exchange  = exchange.upper(),
        min_score = min_score,
        sector    = sector,
        top_n     = top_n,
    )

    background_tasks.add_task(_run_pipeline_background, filters)

    return {
        "status":  "started",
        "message": f"Scanning all {exchange} stocks · ₹{price_min}–₹{price_max} · Top {top_n} picks",
        "filters": {
            "price_min": price_min,
            "price_max": price_max if price_max < 99999 else "no limit",
            "exchange":  exchange,
            "min_score": min_score,
            "sector":    sector,
            "top_n":     top_n,
        }
    }


@router.get("/api/status")
async def get_status():
    """Return current bot status."""
    all_reports = _load_all_reports()
    return {
        "status":           "running" if _pipeline_state["running"] else "idle",
        "pipeline_running": _pipeline_state["running"],
        "last_run":         _pipeline_state.get("last_run"),
        "last_error":       _pipeline_state.get("last_error"),
        "last_filters":     _pipeline_state.get("last_filters"),
        "total_scans":      len(all_reports),
        "model_loaded":     os.path.exists(ML_MODEL_PATH),
    }

from fetcher.stock_list import get_full_universe

@router.get("/api/search")
async def search_universe(q: str = Query(..., min_length=2, description="Search query")):
    """Fuzzy search across all ~7200 stocks by symbol or name."""
    try:
        universe = get_full_universe()
        query = q.lower()
        
        # Match symbol first
        symbol_matches = universe[universe['symbol'].str.lower().str.contains(query, na=False)]
        
        # Match name
        name_matches = universe[universe['name'].str.lower().str.contains(query, na=False)]
        
        # Combine and deduplicate
        import pandas as pd
        combined = pd.concat([symbol_matches, name_matches]).drop_duplicates(subset=['symbol'])
        
        # Return top 15 matches
        results = combined.head(15)[['symbol', 'name', 'exchange']].to_dict(orient='records')
        return results
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return []

@router.get("/api/analyze/{symbol}")
async def analyze_single_stock(symbol: str):
    """Run the analysis pipeline on-demand for a single stock."""
    universe = get_full_universe()
    stock_row = universe[universe['symbol'].str.upper() == symbol.upper()]
    
    if stock_row.empty:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found in database.")
        
    try:
        # Run pipeline forcing ONLY this stock, ignoring filters like price_min/score_min
        # We set min_score=0 so it doesn't get filtered out at the end.
        filters = ScanFilters(min_score=0)
        results = run_pipeline(filters=filters, symbols=[symbol.upper()])
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Could not compute analysis for {symbol}")
            
        return results[0]
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/build-pool")
async def trigger_pool_build(background_tasks: BackgroundTasks):
    """Trigger the overnight candidate pool build (Top 500 stocks)."""
    from main_pipeline import build_candidate_pool
    background_tasks.add_task(build_candidate_pool, 500)
    return {
        "status": "started",
        "message": "Building candidate pool of 500 stocks in background..."
    }


@router.get("/api/pool-status")
async def get_pool_status():
    """Return when candidate pool was last built and total candidates."""
    from main_pipeline import load_candidate_pool
    pool = load_candidate_pool()
    if not pool:
        return {
            "has_pool": False,
            "message": "No candidate pool built yet."
        }
    return {
        "has_pool": True,
        "updated_at": pool.get("updated_at"),
        "total_candidates": pool.get("total_candidates", 0),
    }
