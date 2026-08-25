import React from 'react';

export default function WhyModal({ stock, onClose }) {
  if (!stock) return null;

  const { name, symbol, exchange, sector, current_price, target_price, ai_score, fundamental_score, technical_score, why } = stock;
  const upside = target_price && current_price
    ? (((target_price - current_price) / current_price) * 100).toFixed(1)
    : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div className="modal-header">
          <div className="modal-company">
            <div className="modal-name">{name}</div>
            <div className="modal-meta">
              {symbol} · {exchange} · {sector}
              {upside && <> · Target +{upside}%</>}
            </div>
          </div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        {/* Score Row */}
        <div className="modal-scores">
          <div className="modal-score-cell">
            <span className="modal-score-lbl">AI Score</span>
            <span className="modal-score-val" style={{ color: 'var(--c-blue)' }}>{ai_score}</span>
          </div>
          <div className="modal-score-cell">
            <span className="modal-score-lbl">Fundamental</span>
            <span className="modal-score-val">{fundamental_score}<span style={{ fontSize: '12px', color: 'var(--txt-3)', fontFamily: 'var(--font)' }}>/50</span></span>
          </div>
          <div className="modal-score-cell">
            <span className="modal-score-lbl">Technical</span>
            <span className="modal-score-val">{technical_score}<span style={{ fontSize: '12px', color: 'var(--txt-3)', fontFamily: 'var(--font)' }}>/50</span></span>
          </div>
        </div>

        {/* Narratives */}
        <div className="modal-body">
          {why?.summary && (
            <div className="modal-summary">{why.summary}</div>
          )}

          <div className="narrative-section">
            <div className="narr-label past">Past · 6–12 Month History</div>
            <div className="narr-text">{why?.past || 'Historical context not available.'}</div>
          </div>

          <div className="narrative-section">
            <div className="narr-label now">Present · Why Recommended Today</div>
            <div className="narr-text">{why?.present || 'Trigger analysis not available.'}</div>
          </div>

          <div className="narrative-section">
            <div className="narr-label future">Future · 8–9 Month Outlook</div>
            <div className="narr-text">{why?.future || 'Outlook projection not available.'}</div>
          </div>
        </div>

      </div>
    </div>
  );
}
