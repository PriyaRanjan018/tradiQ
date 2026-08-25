import React from 'react';

export default function StatsBar({ picks, runDate }) {
  if (!picks || picks.length === 0) return null;

  const totalPicks = picks.length;
  const avgUpside = (
    picks.reduce((acc, p) => {
      if (p.target_price && p.current_price) {
        return acc + ((p.target_price - p.current_price) / p.current_price) * 100;
      }
      return acc;
    }, 0) / totalPicks
  ).toFixed(1);

  const topPick = picks[0];

  return (
    <div className="stats-grid">
      <div className="stat-card">
        <div className="stat-card-label">Weekly Recommendations</div>
        <div className="stat-card-value">{totalPicks} Stocks</div>
        <div className="stat-card-subtext">Filtered from 4,800+ NSE & BSE stocks</div>
      </div>

      <div className="stat-card">
        <div className="stat-card-label">Avg Projected Growth</div>
        <div className="stat-card-value" style={{ color: '#ffffff' }}>
          +{avgUpside}%
        </div>
        <div className="stat-card-subtext">8–9 Month Horizon</div>
      </div>

      <div className="stat-card">
        <div className="stat-card-label">Top Recommendation</div>
        <div className="stat-card-value" style={{ color: '#ffffff' }}>
          {topPick?.name || '—'}
        </div>
        <div className="stat-card-subtext">
          AI Score: {topPick?.ai_score}/100 · CMP: ₹{topPick?.current_price}
        </div>
      </div>

      <div className="stat-card">
        <div className="stat-card-label">Last Report Date</div>
        <div className="stat-card-value" style={{ fontSize: '1.3rem' }}>
          {runDate || 'Today'}
        </div>
        <div className="stat-card-subtext">Automated Sunday 9 AM scan</div>
      </div>
    </div>
  );
}
