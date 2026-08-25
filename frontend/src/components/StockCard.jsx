import React from 'react';

const SIGNAL_MAP = {
  rsi: 'RSI Oversold',
  macd_crossover: 'MACD Cross',
  ema_crossover: 'EMA Cross',
  volume_spike: 'Volume Spike',
  near_52w_low: '52W Low',
  bollinger_squeeze: 'BB Squeeze',
};

const SCORE_COLOR = (score) => {
  if (score >= 85) return 'var(--c-green)';
  if (score >= 70) return 'var(--c-blue)';
  return 'var(--c-amber)';
};

export default function StockCard({ stock, onSelectWhy, onOpenAlertModal }) {
  const {
    rank, name, symbol, exchange, sector, industry,
    current_price, target_price, low_52w, high_52w,
    ai_score, fundamental_score, technical_score,
    tech_signals, why,
  } = stock;

  const upside = target_price && current_price
    ? (((target_price - current_price) / current_price) * 100).toFixed(1)
    : null;

  const signals = Object.entries(tech_signals || {})
    .filter(([, v]) => v)
    .map(([k]) => SIGNAL_MAP[k] || k);

  const scoreColor = SCORE_COLOR(ai_score);

  return (
    <article className="sc">
      {/* ── Header ─────────────────────────────────── */}
      <div className="sc-header">
        <div className="sc-company">
          <div className="sc-rank">#{rank}</div>
          <div>
            <div className="sc-name">{name}</div>
            <div className="sc-meta">
              <span className="sc-symbol">{symbol}</span>
              <span className="sc-dot" />
              <span className="sc-sector">{sector}</span>
              <span className={`sc-exchange ${exchange}`}>{exchange}</span>
            </div>
          </div>
        </div>
        <div className="sc-score-ring" style={{ '--sc': `${ai_score}`, '--sc-color': scoreColor }}>
          <span className="sc-score-num">{ai_score.toFixed(0)}</span>
          <span className="sc-score-lbl">/ 100</span>
        </div>
      </div>

      {/* ── Price Grid ─────────────────────────────── */}
      <div className="sc-price-grid">
        <div className="sc-price-cell">
          <span className="sc-plbl">Current Price</span>
          <span className="sc-pval">₹{current_price?.toLocaleString('en-IN')}</span>
        </div>
        <div className="sc-price-cell sc-price-target">
          <span className="sc-plbl">Target · 8-9M</span>
          <span className="sc-pval green">
            ₹{target_price?.toLocaleString('en-IN')}
            {upside && <span className="sc-upside">+{upside}%</span>}
          </span>
        </div>
        <div className="sc-price-cell">
          <span className="sc-plbl">52W Low</span>
          <span className="sc-pval muted">₹{low_52w?.toLocaleString('en-IN')}</span>
        </div>
        <div className="sc-price-cell">
          <span className="sc-plbl">52W High</span>
          <span className="sc-pval muted">₹{high_52w?.toLocaleString('en-IN')}</span>
        </div>
      </div>

      {/* ── Score Bar ──────────────────────────────── */}
      <div className="sc-score-bar-wrap">
        <div className="sc-score-row">
          <span>Fundamental <strong>{fundamental_score}/50</strong></span>
          <span>Technical <strong>{technical_score}/50</strong></span>
        </div>
        <div className="sc-bar-bg">
          <div
            className="sc-bar-fill"
            style={{ width: `${ai_score}%`, background: scoreColor }}
          />
        </div>
      </div>

      {/* ── Signals ────────────────────────────────── */}
      {signals.length > 0 && (
        <div className="sc-signals">
          {signals.map(s => (
            <span key={s} className="sc-signal">{s}</span>
          ))}
        </div>
      )}

      {/* ── Summary ────────────────────────────────── */}
      {why?.summary && (
        <p className="sc-summary">{why.summary}</p>
      )}

      {/* ── Action Buttons ─────────────────────────── */}
      <div className="sc-actions">
        <button className="sc-why-btn" onClick={() => onSelectWhy(stock)}>
          View Full Analysis
        </button>
        <button className="sc-alert-btn" onClick={() => onOpenAlertModal(stock)}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{marginRight: '2px'}}>
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
          Add Alert
        </button>
      </div>
    </article>
  );
}
