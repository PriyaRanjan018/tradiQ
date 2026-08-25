import React, { useState, useEffect } from 'react';
import { API_BASE } from '../config';

export default function Header({ scanning, runDate, hasScanned, alertCount, onToggleNotifications }) {
  const [poolStatus, setPoolStatus] = useState({ has_pool: false, total_candidates: 0, updated_at: null });

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
    const interval = setInterval(fetchPoolStatus, 30000); // refresh every 30 s
    return () => clearInterval(interval);
  }, []);

  // Format pool updated_at nicely
  const poolUpdatedLabel = () => {
    if (!poolStatus.updated_at) return null;
    try {
      const d = new Date(poolStatus.updated_at);
      return d.toLocaleString('en-IN', {
        day: '2-digit', month: 'short',
        hour: '2-digit', minute: '2-digit',
      });
    } catch { return poolStatus.updated_at; }
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
        {/* Auto Candidate Pool Status — read-only badge (no button) */}
        <div
          title={
            poolStatus.has_pool
              ? `Pool auto-updated at ${poolStatus.updated_at}. Next refresh: tonight 2:00 AM IST.`
              : 'Candidate pool is being built automatically tonight at 2:00 AM IST.'
          }
          style={{
            display: 'flex', alignItems: 'center', gap: '6px',
            background: poolStatus.has_pool ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
            border: `1px solid ${poolStatus.has_pool ? '#10b981' : '#f59e0b'}`,
            color: poolStatus.has_pool ? '#10b981' : '#f59e0b',
            borderRadius: '6px', padding: '5px 10px', fontSize: '12px', fontWeight: 600,
            cursor: 'default', userSelect: 'none',
          }}
        >
          <span>{poolStatus.has_pool ? '⚡' : '🌙'}</span>
          <span>
            {poolStatus.has_pool
              ? `Pool · ${poolStatus.total_candidates} stocks · ${poolUpdatedLabel()}`
              : 'Pool builds tonight 2:00 AM'}
          </span>
        </div>

        {/* Notification Bell */}
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
        <div className="schedule-tag">Auto · 02:00 AM &amp; Sat 23:00 &amp; Sun 09:00</div>
      </div>
    </header>
  );
}
