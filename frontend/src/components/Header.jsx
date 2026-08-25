import React from 'react';

export default function Header({ scanning, runDate, hasScanned, alertCount, onToggleNotifications }) {
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
        <div className="schedule-tag">Auto · Every Sunday 09:00</div>
      </div>
    </header>
  );
}
