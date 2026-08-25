"""
TradiQ — Stock Universe Fetcher
Fetches all NSE (2,296) + BSE (4,976) listed stocks dynamically from official exchange endpoints.
"""

import requests
import pandas as pd
import io
import os
import json
import logging
from datetime import datetime, timedelta
from config.settings import CACHE_DIR, NSE_SUFFIX, BSE_SUFFIX

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bseindia.com/",
}


def _cache_path(name: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{name}.json")


def _is_cache_valid(path: str, ttl_hours: int = 168) -> bool:  # 7 days cache
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    return datetime.now() - mtime < timedelta(hours=ttl_hours)


def fetch_nse_symbols() -> pd.DataFrame:
    """Download all NSE-listed equity symbols (2,296 stocks)."""
    cache = _cache_path("nse_symbols")
    if _is_cache_valid(cache):
        try:
            return pd.DataFrame(json.load(open(cache)))
        except Exception:
            pass

    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip() for c in df.columns]
            if "SERIES" in df.columns:
                df = df[df["SERIES"] == "EQ"]
            symbol_col = "SYMBOL" if "SYMBOL" in df.columns else df.columns[0]
            name_col   = "NAME OF COMPANY" if "NAME OF COMPANY" in df.columns else df.columns[1]

            df = df.rename(columns={symbol_col: "symbol", name_col: "name"})
            df["exchange"]  = "NSE"
            df["yf_ticker"] = df["symbol"].astype(str) + NSE_SUFFIX
            res = df[["symbol", "name", "exchange", "yf_ticker"]].reset_index(drop=True)
            json.dump(res.to_dict(orient="records"), open(cache, "w"), indent=2)
            logger.info(f"NSE universe: {len(res)} stocks loaded")
            return res
    except Exception as e:
        logger.warning(f"NSE fetch notice ({e}), loading from disk cache")

    if os.path.exists(cache):
        return pd.DataFrame(json.load(open(cache)))

    return pd.DataFrame(columns=["symbol", "name", "exchange", "yf_ticker"])


def fetch_bse_symbols() -> pd.DataFrame:
    """Download all BSE-listed equity symbols (4,976 stocks)."""
    cache = _cache_path("bse_symbols")
    if _is_cache_valid(cache):
        try:
            return pd.DataFrame(json.load(open(cache)))
        except Exception:
            pass

    try:
        url = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            rows = []
            if isinstance(data, list):
                for item in data:
                    code = str(item.get("SCRIP_CD", "")).strip()
                    symbol = str(item.get("scrip_id", "")).strip() or code
                    name = str(item.get("Issuer_Name", "")).strip() or str(item.get("Scrip_Name", "")).strip()
                    if code:
                        rows.append({
                            "symbol": symbol,
                            "name": name,
                            "exchange": "BSE",
                            "yf_ticker": code + BSE_SUFFIX,
                        })
            res = pd.DataFrame(rows)
            if not res.empty:
                json.dump(res.to_dict(orient="records"), open(cache, "w"), indent=2)
                logger.info(f"BSE universe: {len(res)} stocks loaded")
                return res
    except Exception as e:
        logger.warning(f"BSE fetch notice ({e}), loading from disk cache")

    if os.path.exists(cache):
        return pd.DataFrame(json.load(open(cache)))

    return pd.DataFrame(columns=["symbol", "name", "exchange", "yf_ticker"])


def get_full_universe() -> pd.DataFrame:
    """Returns combined NSE + BSE stock universe (~7,200 stocks total)."""
    nse_df = fetch_nse_symbols()
    bse_df = fetch_bse_symbols()

    combined = pd.concat([nse_df, bse_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["yf_ticker"], keep="first").reset_index(drop=True)
    logger.info(f"Full Stock Universe: {len(combined)} active stocks (NSE + BSE)")
    return combined
