# TradiQ — Scoring & AI Model: Complete Technical Documentation

> **Source of truth:** All numbers in this document are sourced directly from the backend Python source code in `/backend/config/settings.py`, `/backend/analysis/technical.py`, `/backend/analysis/fundamental.py`, `/backend/analysis/composite_score.py`, and `/backend/ml/`.

---

## 1. Overview: How a Stock Gets Its Score

Every stock goes through **4 scoring stages** in this order:

```
Raw Data (yfinance)
    │
    ▼
[Stage 1] Fundamental Score    →   0–50 pts   (6 metrics)
[Stage 2] Technical Score      →   0–50 pts   (6 indicators)
    │
    ▼
[Stage 3] Composite Score  =  Fundamental + Technical  →  0–100 pts
    │
    ▼
[Stage 4] AI Score
    • If XGBoost model is trained → model.predict_proba() × 100
    • If model NOT trained yet    → AI Score = Composite Score (fallback)
```

**Final ranking is done on AI Score (descending).**

---

## 2. Fundamental Score (0–50 points)

Fundamental data is fetched from **Yahoo Finance** (`yfinance`) for each stock. Six metrics are evaluated and scored independently.

### 2.1 Score Weight Table

| Metric | Max Points | What It Measures |
|:---|:---:|:---|
| Revenue Growth YoY | 10 | Year-on-year revenue increase |
| Profit Growth QoQ | 10 | Quarter-on-quarter profit increase |
| PE vs Sector Average | 8 | Is the stock cheap relative to peers? |
| Debt-to-Equity | 8 | How much debt the company carries |
| Return on Equity (ROE) | 7 | Efficiency of profit generation |
| Promoter Holding | 7 | Owner/founder stake in the company |
| **Total** | **50** | |

---

### 2.2 Metric-by-Metric Calculation

#### **Revenue Growth YoY** — Max 10 pts
```
Source field: fund["revenue_growth_yoy"]  (percentage, e.g. 25.0 = 25%)

if growth >= 20%  →  10 pts  (Full)
if growth >= 10%  →   5 pts  (Half)
if growth <  10%  →   0 pts
```

#### **Profit Growth QoQ** — Max 10 pts
```
Source field: fund["qoq_profit_growth"] or fund["earnings_growth"]

if growth >= 15%  →  10 pts  (Full)
if growth >=  5%  →   5 pts  (Half)
if growth <   5%  →   0 pts
```

#### **PE vs Sector Average** — Max 8 pts

The stock's PE is compared against its **sector's average PE** (e.g., IT sector avg is ~30, Consumer sector avg is ~40). The idea: a stock trading at a discount to its peers is potentially undervalued.

```
discount_pct = (sector_avg_PE - stock_PE) / sector_avg_PE × 100

if discount_pct >= 10%  →  8 pts  (Full — clearly cheap)
if discount_pct >=  5%  →  4 pts  (Half — moderately cheap)
if discount_pct <   5%  →  0 pts  (Fairly priced or expensive)
```

#### **Debt-to-Equity** — Max 8 pts
```
Source field: fund["debt_to_equity"]

if D/E <= 1.0  →  8 pts  (Full — low debt, conservative)
if D/E <= 2.0  →  4 pts  (Half — moderate debt)
if D/E >  2.0  →  0 pts  (High leverage, risky)

Special: if D/E is UNKNOWN (None) → 4 pts (neutral, neither rewarded nor penalized)
```

#### **Return on Equity (ROE)** — Max 7 pts
```
Source field: fund["roe"]  (percentage)

if ROE >= 15%  →  7 pts  (Full — efficient company)
if ROE >= 10%  →  3.5 pts (Half)
if ROE <  10%  →  0 pts
```

#### **Promoter Holding** — Max 7 pts
```
Source field: fund["promoter_holding"]  (percentage of shares held by founders/promoters)

if holding >= 60%  →  7 pts  (Full — founders are committed)
if holding >= 50%  →  3.5 pts (Half)
if holding <  50%  →  0 pts
```

---

## 3. Technical Score (0–50 points)

Technical data is computed from **1 year of daily OHLCV** (Open, High, Low, Close, Volume) price history using standard indicator formulas. All implemented from scratch using `pandas` and `numpy` — no third-party indicator library.

**Minimum data requirement:** >= 50 trading days of price history. Stocks with less history receive 0.

### 3.1 Score Weight Table

| Indicator | Max Points | Signal Description |
|:---|:---:|:---|
| RSI (14-day) | 10 | Oversold recovery zone |
| MACD Crossover | 10 | Bullish momentum crossover |
| EMA Golden Cross (20/50) | 8 | Short-term trend above long-term |
| Volume Spike | 8 | Unusual buying activity |
| Near 52-Week Low | 7 | Price at historical support |
| Bollinger Band Squeeze | 7 | Volatility compression before breakout |
| **Total** | **50** | |

---

### 3.2 Indicator-by-Indicator Calculation

#### **RSI (Relative Strength Index)** — Max 10 pts

```python
# Formula: Wilder's smoothed EMA of gains/losses over 14 days
delta    = close.diff()
avg_gain = gains.ewm(com=13, min_periods=14).mean()
avg_loss = losses.ewm(com=13, min_periods=14).mean()
RS       = avg_gain / avg_loss
RSI      = 100 - (100 / (1 + RS))
```

```
Threshold: 30 <= RSI <= 50

RSI in [30, 50]  →  10 pts
  Rationale: RSI in this range means the stock recently was oversold
  (RSI < 30) and is now recovering. This is the sweet spot — not
  too far gone, not already overbought.

RSI < 30  →  0 pts  (Deeply oversold, may still be falling)
RSI > 50  →  0 pts  (Already recovered, momentum advantage gone)
```

#### **MACD Crossover** — Max 10 pts

```python
# Standard MACD parameters: fast=12, slow=26, signal=9
ema_fast    = close.ewm(span=12).mean()
ema_slow    = close.ewm(span=26).mean()
macd_line   = ema_fast - ema_slow
signal_line = macd_line.ewm(span=9).mean()
histogram   = macd_line - signal_line
```

```
Signal fires if EITHER:
  1. Bullish crossover: histogram[today] > 0 AND histogram[yesterday] <= 0
     (MACD just crossed above the signal line)
  OR
  2. MACD > signal_line AND histogram is rising
     (Momentum building but crossover just starting)

If signal = True  →  10 pts
If signal = False →   0 pts
```

#### **EMA Golden Cross (20-day vs 50-day)** — Max 8 pts

```python
ema20 = close.ewm(span=20).mean()
ema50 = close.ewm(span=50).mean()
```

```
Signal = ema20[-1] > ema50[-1]
  (Short-term average is above long-term average = uptrend)

Bonus check: Did this cross happen recently (within last 10 days)?
  → Same 8 pts (full score for fresh cross)

If ema20 > ema50  →  8 pts
If ema20 <= ema50 →  0 pts
```

#### **Volume Spike** — Max 8 pts

```python
avg_vol_20 = volume.tail(20).mean()   # 20-day average volume
vol_ratio  = today_volume / avg_vol_20
```

```
Threshold: VOLUME_SPIKE_MULT = 1.5

if vol_ratio >= 1.5  →  8 pts  (Full — major buying interest)
if vol_ratio >= 1.2  →  4 pts  (Half — above-average activity)
if vol_ratio <  1.2  →  0 pts
```

#### **Near 52-Week Low** — Max 7 pts

```python
low_52w       = low.tail(252).min()   # 252 trading days ≈ 1 year
pct_from_low  = (current_price - low_52w) / low_52w
```

```
Threshold: NEAR_52W_LOW_PCT = 0.20  (20%)

if pct_from_low <= 20%  →  7 pts  (Full — near support, high reward/risk)
if pct_from_low <= 35%  →  3.5 pts (Half)
if pct_from_low >  35%  →  0 pts

Rationale: Stocks near their 52-week lows often have limited downside
and significant upside if the fundamentals are sound.
```

#### **Bollinger Band Squeeze** — Max 7 pts

```python
# 20-day window, 2 standard deviations
sma        = close.rolling(20).mean()
std        = close.rolling(20).std()
upper_band = sma + 2 * std
lower_band = sma - 2 * std
bb_width   = (upper_band - lower_band) / sma   # Normalized width
```

```
Threshold: BB_SQUEEZE_WIDTH = 0.05

if bb_width <= 0.05  →  7 pts  (Full — very tight squeeze)
if bb_width <= 0.08  →  3.5 pts (Half — moderate squeeze)
if bb_width >  0.08  →  0 pts

Rationale: When Bollinger Bands narrow, volatility is at a minimum.
Historically, this compression often precedes a large directional move.
```

---

## 4. Composite Score (0–100)

Simple addition:

```
Composite Score = Fundamental Score + Technical Score
               = (0–50) + (0–50)
               = 0–100
```

This is a **purely rule-based, weighted score**. No machine learning is involved at this stage.

---

## 5. AI Score — XGBoost Classifier

### 5.1 Architecture

The system uses **XGBoost** (eXtreme Gradient Boosting), an ensemble of decision trees, implemented via the `xgboost` Python library (`XGBClassifier`).

```
Model type:   XGBClassifier (binary classification)
Label:        1 = stock grew > 40% within 9 months of scanning
              0 = stock did NOT grow > 40%
Output:       predict_proba() → probability of class 1
AI Score:     probability × 100   (maps 0.0–1.0 → 0–100)
```

### 5.2 Training Hyperparameters

```python
XGBClassifier(
    n_estimators     = 300,    # 300 trees in the ensemble
    max_depth        = 6,      # Each tree can be at most 6 levels deep
    learning_rate    = 0.05,   # Small step size → slower but more accurate
    subsample        = 0.8,    # Use 80% of rows per tree (prevents overfitting)
    colsample_bytree = 0.8,    # Use 80% of features per tree
    scale_pos_weight = neg/pos # Adjusts for class imbalance
                               # (most stocks don't grow 40% in 9 months)
)
```

### 5.3 Feature Vector (24 features)

Every stock is converted into a 24-dimensional numeric vector:

| # | Feature | Source |
|:--|:---|:---|
| 1 | `pe_ratio` | P/E ratio from Yahoo Finance |
| 2 | `pb_ratio` | Price-to-Book ratio |
| 3 | `debt_to_equity` | D/E ratio |
| 4 | `roe` | Return on Equity % |
| 5 | `revenue_growth_yoy` | Revenue growth YoY % |
| 6 | `qoq_profit_growth` | Profit growth QoQ % |
| 7 | `promoter_holding` | Promoter shareholding % |
| 8 | `profit_margins` | Net profit margin % |
| 9 | `market_cap_cr` | Market cap in Crore (INR) |
| 10 | `earnings_growth` | YoY earnings growth % |
| 11 | `rsi_value` | Raw RSI value (0–100) |
| 12 | `macd_value` | Raw MACD line value |
| 13 | `ema20` | 20-day EMA price |
| 14 | `ema50` | 50-day EMA price |
| 15 | `ema_diff_pct` | (EMA20 − EMA50) / EMA50 × 100 |
| 16 | `volume_ratio` | Today's volume / 20-day avg volume |
| 17 | `pct_from_52w_low` | % above 52-week low |
| 18 | `bb_width` | Normalized Bollinger Band width |
| 19 | `return_1m` | 1-month price return % |
| 20 | `return_3m` | 3-month price return % |
| 21 | `return_6m` | 6-month price return % |
| 22 | `return_1y` | 1-year price return % |
| 23 | `fundamental_score` | Output from Stage 2 (0–50) |
| 24 | `technical_score` | Output from Stage 1 (0–50) |

Missing values are filled with `0.0`.

### 5.4 Training Label

```python
label = 1   # if stock_price grew > 40% within 9 months of the scan date
label = 0   # otherwise
```

### 5.5 Current Status (Honest Note)

> **The XGBoost model is NOT yet trained** because it requires historical labeled data (`data/training_data.jsonl`) — i.e., past scan records linked to actual future price outcomes.
>
> **Currently, the AI Score = Composite Score** (the rule-based 0–100 sum of fundamental + technical).
> The XGBoost model is designed to be trained once enough historical data is collected. This is by design — the codebase is fully wired to use the model the moment it is trained.

---

## 6. Target Price Estimation (8–9 Month Horizon)

The target price is a **heuristic estimate**, not a DCF (Discounted Cash Flow) model.

```python
multiplier = 1.0

# Step 1: Revenue growth premium (capped at +30%)
if revenue_growth_yoy > 0:
    multiplier += min(revenue_growth_yoy * 0.03, 0.30)

# Step 2: Forward PE expansion premium (+8%)
if forward_PE < trailing_PE:
    multiplier += 0.08

# Step 3: Technical momentum premium (up to +15%)
multiplier += (technical_score / 50) * 0.15

# Step 4: Bollinger squeeze breakout premium (+10%)
if bollinger_squeeze_signal == True:
    multiplier += 0.10

# Step 5: Confidence haircut
# High score → less haircut. Low score → more conservative.
confidence_factor = composite_score / 100
multiplier = 1 + (multiplier - 1) * confidence_factor

# Final target
target_price = current_price * multiplier
```

**Example for a stock scoring 80/100 with 25% revenue growth:**
```
Base multiplier components:
  + revenue growth: min(25 * 0.03, 0.30) = 0.30
  + technical (perfect): (50/50) * 0.15  = 0.15
  + bollinger squeeze:                      0.10
  = raw multiplier: 1.55

After confidence haircut (score=80):
  multiplier = 1 + (0.55 * 0.80) = 1.44

Target = current_price * 1.44  →  +44% upside estimate
```

---

## 7. Pipeline Flow Summary

```
7,200 NSE + BSE stocks
        │
        ▼ Stage 0: Universe fetch (NSE CSV + BSE CSV)
        │
        ▼ Stage 1: Fast price & volume pre-filter
             • Price: ₹10 – ₹2,000 (configurable)
             • Market Cap: >= ₹50 Crore
             • Avg Daily Volume: >= 50,000 shares
        │
        ▼ Stage 2: Fetch fundamentals (parallel, 20 threads)
        │
        ▼ Stage 3: Score each candidate
             • Technical Score (0–50)
             • Fundamental Score (0–50)
             • Composite Score = sum
             • AI Score = XGBoost(features) × 100  [or fallback = composite]
        │
        ▼ Stage 4: Filter by min AI Score (default: >= 65)
        │
        ▼ Stage 5: Rank by AI Score → Top 20 returned
```

---

## 8. Data Sources

| Data | Source | Method |
|:---|:---|:---|
| Stock List (NSE) | NSE India CSV | Pre-bundled, updated manually |
| Stock List (BSE) | BSE India CSV | Pre-bundled, updated manually |
| Price / OHLCV | Yahoo Finance | `yfinance.download()` batch |
| Fundamentals | Yahoo Finance | `yfinance.Ticker.info` |
| Sector PE Averages | Hard-coded reference table | In `fetcher/fundamentals.py` |

---

## 9. Honest Limitations

| Limitation | Reality |
|:---|:---|
| **Yahoo Finance data quality** | yfinance is an unofficial API. Fundamental data (especially for small-cap BSE stocks) is often missing or stale. |
| **No real backtesting** | The scoring weights (10, 10, 8, 8, 7, 7 pts) were chosen based on financial research intuition, not statistical optimization on historical data. |
| **XGBoost not yet trained** | Currently the AI Score = Composite Score. The XGBoost layer exists as infrastructure for when labeled training data is available. |
| **Target price is heuristic** | The multiplier formula is NOT a DCF model. It is a simple heuristic with revenue growth and technical momentum as inputs. Do not treat it as a financial guarantee. |
| **Sector PE is static** | Sector PE averages are hard-coded reference values, not dynamically pulled from live market data. |
| **Not financial advice** | TradiQ is a research and learning project. Scores are academic indicators, not investment recommendations. |

---

## 10. Technology Stack

| Component | Technology |
|:---|:---|
| Backend | Python 3.11, FastAPI, APScheduler |
| Data fetching | `yfinance`, `pandas` |
| Indicator calculation | `pandas`, `numpy` (custom implementations) |
| ML model | `xgboost 2.x`, `scikit-learn`, `joblib` |
| Frontend | React 18, Vite, Vanilla CSS |
| Deployment | Render (Free tier), GitHub |

---

*Document generated from source code of TradiQ — Indian Stock AI Screener.*
*Last updated: August 2026*
