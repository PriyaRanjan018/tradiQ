"""
TradiQ — Global Configuration
All thresholds, constants, and settings live here.
"""

# ── Price Filter ──────────────────────────────────────────────────────────────
PRICE_MIN = 10           # ₹ minimum stock price
PRICE_MAX = 2000         # ₹ maximum stock price (overridable per scan via API)

# ── Liquidity Filter ──────────────────────────────────────────────────────────
MIN_MARKET_CAP_CR = 50          # Minimum market cap in Crores
MIN_AVG_DAILY_VOLUME = 50_000   # Minimum average daily volume (shares)

# ── Fundamental Score Weights (total = 50 points) ─────────────────────────────
FUNDAMENTAL_WEIGHTS = {
    "revenue_growth_yoy": 10,   # Revenue growth Year-on-Year
    "profit_growth_qoq":  10,   # Profit growth Quarter-on-Quarter
    "pe_vs_sector":        8,   # PE ratio vs sector average
    "debt_to_equity":      8,   # Debt-to-equity ratio
    "roe":                 7,   # Return on Equity
    "promoter_holding":    7,   # Promoter shareholding %
}

# ── Fundamental Thresholds ────────────────────────────────────────────────────
REVENUE_GROWTH_GOOD  = 20.0   # % YoY — full points
REVENUE_GROWTH_OK    = 10.0   # % YoY — half points
PROFIT_GROWTH_GOOD   = 15.0   # % QoQ — full points
PROFIT_GROWTH_OK     =  5.0   # % QoQ — half points
PE_DISCOUNT_NEEDED   = 10.0   # % below sector avg to get full points
MAX_DEBT_TO_EQUITY   =  1.0   # full points if below
MAX_DE_HALF          =  2.0   # half points if below
ROE_GOOD             = 15.0   # % — full points
ROE_OK               = 10.0   # % — half points
PROMOTER_HOLDING_GOOD = 60.0  # % — full points
PROMOTER_HOLDING_OK   = 50.0  # % — half points

# ── Technical Score Weights (total = 50 points) ───────────────────────────────
TECHNICAL_WEIGHTS = {
    "rsi":              10,   # RSI (14-day)
    "macd_crossover":   10,   # MACD bullish crossover
    "ema_crossover":     8,   # 20 EMA > 50 EMA (golden cross)
    "volume_spike":      8,   # Volume > 1.5x 20-day average
    "near_52w_low":      7,   # Within 20% of 52-week low
    "bollinger_squeeze": 7,   # Bollinger Band width squeeze
}

# ── Technical Thresholds ─────────────────────────────────────────────────────
RSI_OVERSOLD_LOW  = 30   # RSI below this = deeply oversold
RSI_OVERSOLD_HIGH = 50   # RSI below this = recovering (sweet spot)
VOLUME_SPIKE_MULT = 1.5  # Volume must be this * 20-day avg
NEAR_52W_LOW_PCT  = 0.20 # Within 20% of 52-week low
BB_SQUEEZE_WIDTH  = 0.05 # Bollinger Band width (normalized) for squeeze

# ── AI Model ─────────────────────────────────────────────────────────────────
AI_SCORE_THRESHOLD = 65   # Minimum AI score (0–100) to qualify for top picks
ML_MODEL_PATH = "ml/models/xgboost_v1.pkl"
GROWTH_TARGET_PCT = 40    # Label: stock grew >40% in 9 months = positive class

# ── Output ────────────────────────────────────────────────────────────────────
TOP_N_PICKS = 20          # Number of top stocks to recommend per scan
LOOKBACK_DAYS = 365       # Days of price history to download

# ── Scheduler ─────────────────────────────────────────────────────────────────
SCHEDULE_DAY_OF_WEEK = "sun"    # Sunday
SCHEDULE_HOUR        = 9        # 9 AM
SCHEDULE_MINUTE      = 0        # :00
SCHEDULE_TIMEZONE    = "Asia/Kolkata"

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_DIR = "data/cache"
CACHE_TTL_HOURS = 24    # Re-download if older than this

# ── Data Source ───────────────────────────────────────────────────────────────
NSE_SUFFIX = ".NS"      # yfinance suffix for NSE stocks
BSE_SUFFIX = ".BO"      # yfinance suffix for BSE stocks

