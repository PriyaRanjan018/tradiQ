import React, { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE } from '../config';

/* ─── Small Score Ring ─────────────────────────────── */
function ScoreRing({ score }) {
  const color = score >= 75 ? '#10b981' : score >= 55 ? '#3b82f6' : '#f59e0b';
  return (
    <div style={{
      width: 52, height: 52, borderRadius: '50%',
      border: `3px solid ${color}`,
      background: 'rgba(0,0,0,0.25)',
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      flexShrink: 0,
    }}>
      <span style={{ fontSize: 16, fontWeight: 700, color, lineHeight: 1, fontFamily: 'var(--mono)' }}>{score}</span>
      <span style={{ fontSize: 8, color: 'var(--txt-3)' }}>/ 100</span>
    </div>
  );
}

/* ─── Stock Detail Popup ───────────────────────────── */
function StockPopup({ stock, onClose }) {
  if (!stock) return null;
  const upside = stock.target_price && stock.current_price
    ? (((stock.target_price - stock.current_price) / stock.current_price) * 100).toFixed(1)
    : null;

  return (
    <div className="sp-overlay" onClick={onClose}>
      <div className="sp-box" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="sp-head">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="sp-name">{stock.company_name || stock.symbol}</div>
            <div className="sp-meta-row">
              <span className="sp-ticker">{stock.symbol}</span>
              {stock.sector && <><span className="sp-dot" />  <span className="sp-sector">{stock.sector}</span></>}
              {stock.exchange && <span className={`sc-exchange ${stock.exchange}`}>{stock.exchange}</span>}
            </div>
          </div>
          <ScoreRing score={Math.round(stock.ai_score || 0)} />
          <button className="sp-close" onClick={onClose}>✕</button>
        </div>

        {/* Price Grid */}
        <div className="sp-price-grid">
          <div className="sp-price-cell">
            <div className="sp-plbl">Current Price</div>
            <div className="sp-pval">₹{(stock.current_price || 0).toLocaleString('en-IN')}</div>
          </div>
          <div className="sp-price-cell sp-target-cell">
            <div className="sp-plbl">Target · 8–9M</div>
            <div className="sp-pval green">
              ₹{(stock.target_price || 0).toLocaleString('en-IN')}
              {upside && <span className="sp-upside">+{upside}%</span>}
            </div>
          </div>
          <div className="sp-price-cell">
            <div className="sp-plbl">52W Low</div>
            <div className="sp-pval muted">₹{(stock.low_52w || 0).toLocaleString('en-IN')}</div>
          </div>
          <div className="sp-price-cell">
            <div className="sp-plbl">52W High</div>
            <div className="sp-pval muted">₹{(stock.high_52w || 0).toLocaleString('en-IN')}</div>
          </div>
        </div>

        {/* Score Bars */}
        <div className="sp-scores">
          <div className="sp-score-item">
            <div className="sp-score-label">
              <span>Fundamental</span>
              <strong>{stock.fundamental_score ?? '—'}/50</strong>
            </div>
            <div className="sp-bar-bg">
              <div className="sp-bar-fill" style={{
                width: `${((stock.fundamental_score || 0) / 50) * 100}%`,
                background: '#10b981'
              }} />
            </div>
          </div>
          <div className="sp-score-item">
            <div className="sp-score-label">
              <span>Technical</span>
              <strong>{stock.technical_score ?? '—'}/50</strong>
            </div>
            <div className="sp-bar-bg">
              <div className="sp-bar-fill" style={{
                width: `${((stock.technical_score || 0) / 50) * 100}%`,
                background: '#3b82f6'
              }} />
            </div>
          </div>
        </div>

        {/* Signals */}
        {stock.signals && stock.signals.length > 0 && (
          <div className="sp-signals">
            {stock.signals.map((s, i) => (
              <span key={i} className="sc-signal">{s}</span>
            ))}
          </div>
        )}

        {/* AI Summary */}
        {stock.why_summary && (
          <div className="sp-summary">{stock.why_summary}</div>
        )}
      </div>
    </div>
  );
}

/* ─── Main Component ───────────────────────────────── */
export default function SearchAutocomplete({ onSelectStock }) {
  const [query, setQuery]         = useState('');
  const [results, setResults]     = useState([]);
  const [isOpen, setIsOpen]       = useState(false);
  const [loading, setLoading]     = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);

  // Popup state
  const [popupStock, setPopupStock]     = useState(null);
  const [popupLoading, setPopupLoading] = useState(false);

  const wrapperRef = useRef(null);

  /* Close dropdown on outside click */
  useEffect(() => {
    const fn = e => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener('mousedown', fn);
    return () => document.removeEventListener('mousedown', fn);
  }, []);

  /* Debounced search */
  useEffect(() => {
    if (query.length < 2) { setResults([]); setIsOpen(false); return; }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setResults(data);
        setIsOpen(true);
        setActiveIdx(-1);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [query]);

  /* Open popup with full stock data */
  const openPopup = useCallback(async (symbol) => {
    setIsOpen(false);
    setQuery('');
    setPopupLoading(true);
    setPopupStock({ symbol, company_name: symbol }); // show skeleton
    try {
      const res = await fetch(`${API_BASE}/api/analyze/${symbol}`);
      if (res.ok) {
        const data = await res.json();
        setPopupStock(data);
      }
    } catch (e) { console.error(e); }
    finally { setPopupLoading(false); }
  }, []);

  /* Keyboard nav */
  const handleKey = e => {
    if (!isOpen) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, results.length - 1)); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)); }
    if (e.key === 'Enter' && activeIdx >= 0) { openPopup(results[activeIdx].symbol); }
    if (e.key === 'Escape')    { setIsOpen(false); }
  };

  return (
    <>
      <div className="sa-wrapper" ref={wrapperRef}>
        <div className="sa-input-row">
          <svg className="sa-search-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="sa-input"
            placeholder="Search 7,200+ Indian stocks..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onFocus={() => { if (results.length > 0) setIsOpen(true); }}
            onKeyDown={handleKey}
          />
          {query && (
            <button className="sa-clear" onClick={() => { setQuery(''); setResults([]); setIsOpen(false); }}>✕</button>
          )}
        </div>

        {/* Dropdown */}
        {isOpen && (
          <div className="sa-dropdown">
            {loading && (
              <div className="sa-status">Searching...</div>
            )}
            {!loading && results.length === 0 && (
              <div className="sa-status">No stocks found for "<strong>{query}</strong>"</div>
            )}
            {!loading && results.map((r, idx) => (
              <div
                key={r.symbol}
                className={`sa-item ${activeIdx === idx ? 'sa-item--active' : ''}`}
                onMouseEnter={() => setActiveIdx(idx)}
                onClick={() => openPopup(r.symbol)}
              >
                <div className="sa-item__left">
                  <span className="sa-item__symbol">{r.symbol}</span>
                  <span className="sa-item__name">{r.name}</span>
                </div>
                <span className={`sa-item__exchange ${r.exchange}`}>{r.exchange}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stock Detail Popup */}
      {popupStock && (
        <StockPopup
          stock={popupLoading ? { ...popupStock, _loading: true } : popupStock}
          onClose={() => setPopupStock(null)}
        />
      )}
    </>
  );
}
