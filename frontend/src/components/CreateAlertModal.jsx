import React, { useState } from 'react';

export default function CreateAlertModal({ stock, onClose, onSaveAlert }) {
  if (!stock) return null;

  const { name, symbol, exchange, current_price, target_price, ai_score } = stock;

  const [metric, setMetric] = useState('price');         // 'price' | 'target' | 'score'
  const [operator, setOperator] = useState('>=');        // '>=' | '<='
  const [threshold, setThreshold] = useState(target_price || current_price || 100);
  const [alertType, setAlertType] = useState('alert_only'); // 'alert_only' | 'ato'
  const [note, setNote] = useState('');

  const handleCreate = (e) => {
    e.preventDefault();
    const newAlert = {
      id: Date.now().toString(),
      ticker: stock.ticker,
      symbol,
      name,
      exchange,
      current_price,
      metric,
      operator,
      threshold: Number(threshold),
      alertType,
      note: note || `Alert when ${symbol} ${metric} ${operator} ${threshold}`,
      createdAt: new Date().toISOString(),
      status: 'ACTIVE', // 'ACTIVE' | 'TRIGGERED' | 'PAUSED'
    };
    onSaveAlert(newAlert);
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box alert-modal-box" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-company">
            <div className="modal-title-row">
              <span className="alert-icon-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{color: 'var(--c-blue)'}}>
                  <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                  <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                </svg>
              </span>
              <span className="modal-name">Create Price Alert</span>
            </div>
            <div className="modal-meta">
              {name} ({symbol}) · {exchange} · Last Price: <strong>₹{current_price}</strong>
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <form onSubmit={handleCreate} className="alert-form">
          {/* Zerodha-style natural sentence formula builder */}
          <div className="alert-formula-box">
            <div className="af-row">
              <span className="af-label">If</span>
              <select className="af-select" value={metric} onChange={e => {
                const m = e.target.value;
                setMetric(m);
                if (m === 'target') setThreshold(target_price);
                else if (m === 'score') setThreshold(ai_score);
                else setThreshold(current_price);
              }}>
                <option value="price">Last Price</option>
                <option value="target">Target Price (8-9M)</option>
                <option value="score">AI Score</option>
              </select>

              <span className="af-label">of</span>
              <div className="af-stock-chip">{symbol} ({exchange})</div>

              <span className="af-label">is</span>
              <select className="af-select operator" value={operator} onChange={e => setOperator(e.target.value)}>
                <option value=">=">&gt;= (Greater or equal)</option>
                <option value="<=">&lt;= (Less or equal)</option>
              </select>

              <span className="af-label">than</span>
              <input
                type="number"
                step="0.1"
                className="af-input"
                value={threshold}
                onChange={e => setThreshold(e.target.value)}
                required
              />
            </div>
            <div className="af-hint">
              Last price: ₹{current_price} {target_price && `· Target: ₹${target_price}`}
            </div>
          </div>


          {/* Note Input */}
          <div className="alert-field">
            <label>Note / Reminder (Optional)</label>
            <input
              type="text"
              className="alert-text-input"
              placeholder="e.g. Target reached — review fundamental report before buying"
              value={note}
              onChange={e => setNote(e.target.value)}
            />
          </div>

          {/* Actions */}
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Create Alert
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
