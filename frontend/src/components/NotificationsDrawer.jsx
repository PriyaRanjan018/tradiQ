import React, { useState } from 'react';

export default function NotificationsDrawer({ alerts, isOpen, onClose, onDeleteAlert, onClearAll }) {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState('ALL'); // 'ALL' | 'ACTIVE' | 'TRIGGERED'

  const filteredAlerts = alerts.filter(a => {
    if (activeTab === 'ACTIVE') return a.status === 'ACTIVE';
    if (activeTab === 'TRIGGERED') return a.status === 'TRIGGERED';
    return true;
  });

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-box" onClick={e => e.stopPropagation()}>

        {/* Drawer Header */}
        <div className="drawer-header">
          <div className="drawer-title-group">
            <span className="drawer-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
              </svg>
            </span>
            <div>
              <div className="drawer-title">Notifications & Price Alerts</div>
              <div className="drawer-sub">{alerts.length} alerts active</div>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Tabs */}
        <div className="drawer-tabs">
          <button
            className={`d-tab ${activeTab === 'ALL' ? 'active' : ''}`}
            onClick={() => setActiveTab('ALL')}
          >
            All ({alerts.length})
          </button>
          <button
            className={`d-tab ${activeTab === 'ACTIVE' ? 'active' : ''}`}
            onClick={() => setActiveTab('ACTIVE')}
          >
            Active ({alerts.filter(a => a.status === 'ACTIVE').length})
          </button>
          <button
            className={`d-tab ${activeTab === 'TRIGGERED' ? 'active' : ''}`}
            onClick={() => setActiveTab('TRIGGERED')}
          >
            Triggered ({alerts.filter(a => a.status === 'TRIGGERED').length})
          </button>
        </div>

        {/* Alerts List */}
        <div className="drawer-body">
          {filteredAlerts.length === 0 ? (
            <div className="drawer-empty">
              <div className="de-icon">🔕</div>
              <div className="de-title">No alerts in this category</div>
              <div className="de-sub">Click "+ Add Alert" on any stock card to set up automated price tracking.</div>
            </div>
          ) : (
            <div className="alerts-list">
              {filteredAlerts.map(alert => (
                <div key={alert.id} className={`alert-card ${alert.status.toLowerCase()}`}>
                  <div className="ac-top">
                    <div className="ac-stock-info">
                      <span className="ac-symbol">{alert.symbol}</span>
                      <span className="ac-name">{alert.name}</span>
                    </div>
                    <span className={`ac-badge ${alert.status.toLowerCase()}`}>
                      {alert.status}
                    </span>
                  </div>

                  <div className="ac-condition">
                    If {alert.metric} {alert.operator} <strong>₹{alert.threshold}</strong>
                  </div>

                  {alert.note && (
                    <div className="ac-note">"{alert.note}"</div>
                  )}

                  <div className="ac-footer">
                    <span className="ac-time">
                      Created: {new Date(alert.createdAt).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <button className="ac-delete-btn" onClick={() => onDeleteAlert(alert.id)}>
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {alerts.length > 0 && (
          <div className="drawer-footer">
            <button className="btn-secondary danger" onClick={onClearAll}>
              Clear All Alerts
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
