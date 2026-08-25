"""
TradiQ — Pydantic API Schemas
Defines the shape of all API request/response models.
"""

from pydantic import BaseModel
from typing import Optional, Any


class TechSignals(BaseModel):
    rsi: bool = False
    macd_crossover: bool = False
    ema_crossover: bool = False
    volume_spike: bool = False
    near_52w_low: bool = False
    bollinger_squeeze: bool = False


class TechRaw(BaseModel):
    rsi_value: Optional[float] = None
    macd_value: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    volume_ratio: Optional[float] = None
    pct_from_52w_low: Optional[float] = None
    bb_width: Optional[float] = None
    low_52w: Optional[float] = None


class FundBreakdown(BaseModel):
    revenue_growth: float = 0
    profit_growth: float = 0
    pe_vs_sector: float = 0
    debt_to_equity: float = 0
    roe: float = 0
    promoter_holding: float = 0


class WhyReason(BaseModel):
    past: str        # Historical context
    present: str     # Current signals that triggered the pick
    future: str      # Future outlook and rationale
    summary: str     # One-line card summary


class PriceHistory(BaseModel):
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    return_1y: Optional[float] = None
    avg_volume_20d: Optional[float] = None
    current_price: Optional[float] = None


class StockPick(BaseModel):
    rank: int
    ticker: str
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str

    current_price: Optional[float]
    target_price: Optional[float]
    low_52w: Optional[float]
    high_52w: Optional[float]

    ai_score: float
    composite_score: float
    fundamental_score: float
    technical_score: float

    tech_signals: TechSignals
    tech_raw: TechRaw
    fund_breakdown: FundBreakdown
    price_history: PriceHistory

    why: WhyReason
    run_date: str


class WeeklyReport(BaseModel):
    run_date: str
    total_scanned: int
    total_passed_filter: int
    picks: list[StockPick]


class StatusResponse(BaseModel):
    status: str
    last_run: Optional[str]
    next_run: Optional[str]
    total_reports: int
    model_loaded: bool
