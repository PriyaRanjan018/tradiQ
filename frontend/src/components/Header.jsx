import React, { useState, useEffect } from 'react';
import { API_BASE } from '../config';

export default function Header({ scanning, runDate, hasScanned, alertCount, onToggleNotifications }) {
  const [poolStatus, setPoolStatus] = useState({ has_pool: false, total_candidates: 0, updated_at: null });
  const [isBuildingPool, setIsBuildingPool] = useState(false);

  const fetchPoolStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/pool-status`);
      if (res.ok) {
        const data = await res.json();
        setPoolStatus(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchPoolStatus();
    const interval = setInterval(fetchPoolStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleRebuildPool = async () => {
    if (isBuildingPool) return;
    setIsBuildingPool(true);
    try {
      const res = await fetch(`${API_BASE}/api/build-pool`, { method: 'POST' });
      if (res.ok) {
        alert('⚡ Candidate Pool build started in background (takes ~5-10 mins). Nightly scan will also run automatically at 2:00 AM IST!');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsBuildingPool(false);
    }
  };

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="brand">
          <span className="brand-logo">T</span>
          <div className="brand-text">
            <span className="brand-name">TradiQ</span>
            <span className="brand-sub">AI Stock Screener · India</span>
          </div>
        </div>
      </div>

      <div className="header-center">
        <div className="header-meta">
          <span className="meta-item">
            <span className="meta-label">Universe</span>
            <span className="meta-value">NSE + BSE · ~7,200 stocks</span>
          </span>
          <span className="meta-divider" />
          <span className="meta-item">
            <span className="meta-label">Picks per Scan</span>
            <span className="meta-value">Top 20</span>
          </span>
          <span className="meta-divider" />
          <span className="meta-item">
            <span className="meta-label">Horizon</span>
            <span className="meta-value">8–9 Months</span>
          </span>
          {runDate && (
            <>
              <span className="meta-divider" />
              <span className="meta-item">
                <span className="meta-label">Last Scan</span>
                <span className="meta-value">{runDate}</span>
              </span>
            </>
          )}
        </div>
      </div>

      <div className="header-right">
        {/* Candidate Pool Status */}
        <button
          className="pool-badge-btn"
          onClick={handleRebuildPool}
          title={poolStatus.has_pool ? `Candidate Pool updated at ${poolStatus.updated_at}. Click to refresh manually!` : 'Click to build 500-stock candidate pool in background'}
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            background: poolStatus.has_pool ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
            border: `1px solid ${poolStatus.has_pool ? '#10b981' : '#f59e0b'}`,
            color: poolStatus.has_pool ? '#10b981' : '#f59e0b',
            borderRadius: '6px', padding: '5px 10px', fontSize: '12px', fontWeight: 600, cursor: 'pointer'
          }}
        >
          <span>⚡</span>
          <span>{isBuildingPool ? 'Building Pool...' : poolStatus.has_pool ? `500 Pool Ready` : 'Build Pool'}</span>
        </button>

        {/* Notification Bell Icon Button */}
        <button
          className="nav-bell-btn"
          onClick={onToggleNotifications}
          title="Open Notifications & Alerts"
        >
          <span className="bell-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
              <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
            </svg>
          </span>
          {alertCount > 0 && (
            <span className="bell-badge">{alertCount}</span>
          )}
        </button>

        <div className={`live-badge ${scanning ? 'scanning' : hasScanned ? 'idle' : 'waiting'}`}>
          <span className="live-dot" />
          {scanning ? 'Scanning Market...' : hasScanned ? 'Live Report Ready' : 'Ready to Scan'}
        </div>
        <div className="schedule-tag">Auto · 02:00 AM & Sun 09:00</div>
      </div>
    </header>
  );
}
