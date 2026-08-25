import React, { useState } from 'react';

const PRICE_PRESETS = [
  { label: '₹10 – 300', min: 10, max: 300 },
  { label: '₹10 – 500', min: 10, max: 500 },
  { label: '₹10 – 1,000', min: 10, max: 1000 },
  { label: '₹10 – 2,000', min: 10, max: 2000 },
  { label: 'No Limit', min: 10, max: 99999 },
];

export default function FilterPanel({ filters, sectors, onChange, onScan, scanning, resultCount, totalCount, hasScanned }) {
  const [activePreset, setActivePreset] = useState(3); // ₹10–2000 default

  const set = (patch) => onChange({ ...filters, ...patch });

  const handlePreset = (idx, p) => {
    setActivePreset(idx);
    set({ priceMin: p.min, priceMax: p.max });
  };

  const handleCustomPrice = (key, val) => {
    setActivePreset(null);
    set({ [key]: Number(val) || 0 });
  };

  return (
    <aside className="filter-sidebar">
      {/* Run Scan */}
      <button className="scan-btn" onClick={onScan} disabled={scanning}>
        {scanning ? (
          <><span className="scan-spinner" /> Scanning ~5,200 stocks...</>
        ) : (
          'Run Live Scan → Top 20'
        )}
      </button>

      {/* Result counter */}
      <div className="filter-result-count">
        <span className="frc-num">{resultCount}</span>
        <span className="frc-label">
          {!hasScanned ? 'live stocks loaded' : `of ${totalCount} live picks match`}
        </span>
      </div>

      <div className="filter-divider" />

      {/* Price Range */}
      <div className="filter-section">
        <div className="filter-section-label">Price Range</div>
        <div className="price-presets">
          {PRICE_PRESETS.map((p, i) => (
            <button
              key={i}
              className={`fp-preset ${activePreset === i ? 'active' : ''}`}
              onClick={() => handlePreset(i, p)}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="price-inputs">
          <div className="pi-field">
            <label>Min ₹</label>
            <input
              type="number"
              value={filters.priceMin}
              min={1}
              onChange={e => handleCustomPrice('priceMin', e.target.value)}
            />
          </div>
          <span className="pi-sep">—</span>
          <div className="pi-field">
            <label>Max ₹</label>
            <input
              type="number"
              value={filters.priceMax >= 99999 ? '' : filters.priceMax}
              placeholder="No limit"
              min={1}
              onChange={e => handleCustomPrice('priceMax', e.target.value || 99999)}
            />
          </div>
        </div>
      </div>

      <div className="filter-divider" />

      {/* Exchange */}
      <div className="filter-section">
        <div className="filter-section-label">Exchange</div>
        <div className="seg-control">
          {['ALL', 'NSE', 'BSE'].map(ex => (
            <button
              key={ex}
              className={`seg-btn ${filters.exchange === ex ? 'active' : ''}`}
              onClick={() => set({ exchange: ex })}
            >
              {ex === 'ALL' ? 'All' : ex}
            </button>
          ))}
        </div>
      </div>

      <div className="filter-divider" />

      {/* Sector */}
      <div className="filter-section">
        <div className="filter-section-label">Sector</div>
        <select
          className="filter-select"
          value={filters.sector}
          onChange={e => set({ sector: e.target.value })}
        >
          {sectors.map(s => (
            <option key={s} value={s}>{s === 'ALL' ? 'All Sectors' : s}</option>
          ))}
        </select>
      </div>

      <div className="filter-divider" />

      {/* Min AI Score */}
      <div className="filter-section">
        <div className="filter-section-label">
          Min AI Score
          <span className="filter-section-value">{filters.minScore}/100</span>
        </div>
        <input
          type="range"
          className="score-range"
          min={0} max={95} step={5}
          value={filters.minScore}
          onChange={e => set({ minScore: Number(e.target.value) })}
        />
        <div className="score-range-labels">
          <span>0</span><span>50</span><span>95</span>
        </div>
      </div>

      <div className="filter-divider" />

      {/* Active filters summary */}
      <div className="active-filters">
        <div className="filter-section-label">Active Filters</div>
        <div className="af-tags">
          <span className="af-tag">
            ₹{filters.priceMin.toLocaleString()} – {filters.priceMax >= 99999 ? '∞' : '₹' + filters.priceMax.toLocaleString()}
          </span>
          <span className="af-tag">{filters.exchange}</span>
          {filters.sector !== 'ALL' && <span className="af-tag">{filters.sector}</span>}
          <span className="af-tag">Score ≥ {filters.minScore}</span>
        </div>
      </div>
    </aside>
  );
}
