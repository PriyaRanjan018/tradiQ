import React, { useState } from 'react';
import StockCard from '../components/StockCard';
import WhyModal from '../components/WhyModal';
import FilterPanel from '../components/FilterPanel';
import SearchAutocomplete from '../components/SearchAutocomplete';
import { API_BASE } from '../config';

export default function Dashboard({
  picks, allPicks, scanning, hasScanned,
  filters, sectors, onFiltersChange, onScan,
  onSelectWhy, selectedWhyStock, onCloseWhyModal,
  onOpenAlertModal
}) {
  const [sortBy, setSortBy] = useState('ai_score');
  const [onDemandStocks, setOnDemandStocks] = useState([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const handleSelectStock = async (symbol) => {
    if (onDemandStocks.find(s => s.symbol === symbol)) return;
    
    setIsAnalyzing(true);
    try {
      const res = await fetch(`${API_BASE}/api/analyze/${symbol}`);
      if (!res.ok) {
        const errorData = await res.json();
        alert(`Error: ${errorData.detail || 'Could not analyze stock'}`);
        return;
      }
      const data = await res.json();
      setOnDemandStocks(prev => [data, ...prev]);
    } catch (err) {
      console.error(err);
      alert('Failed to analyze stock. See console for details.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Deduplicate and combine picks with onDemandStocks
  const stockMap = new Map();
  picks.forEach(p => stockMap.set(p.symbol, p));
  onDemandStocks.forEach(p => stockMap.set(p.symbol, p));

  const combinedDisplay = Array.from(stockMap.values())
    .sort((a, b) => {
      if (sortBy === 'upside') {
        return (b.target_price - b.current_price) / b.current_price - (a.target_price - a.current_price) / a.current_price;
      }
      if (sortBy === 'price') return a.current_price - b.current_price;
      return b.ai_score - a.ai_score;
    })
    .map((stock, idx) => ({
      ...stock,
      rank: idx + 1 // Dynamically re-rank sequentially #1, #2, #3...
    }));

  return (
    <div className="dashboard-layout">
      {/* Sidebar */}
      <FilterPanel
        filters={filters}
        sectors={sectors}
        onChange={onFiltersChange}
        onScan={onScan}
        scanning={scanning}
        resultCount={combinedDisplay.length}
        totalCount={allPicks.length}
        hasScanned={hasScanned}
      />

      {/* Main Content Area */}
      <main className="dashboard-main">
        {/* Toolbar */}
        <div className="toolbar">
          <SearchAutocomplete onSelectStock={handleSelectStock} />
          
          <div className="toolbar-right">
            <span className="toolbar-count">
              {scanning || isAnalyzing
                ? 'Scanning...'
                : <><strong>{combinedDisplay.length}</strong> stocks shown</>
              }
            </span>
            <div className="sort-control">
              <span className="sort-label">Sort by</span>
              <select
                className="sort-select"
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
              >
                <option value="ai_score">AI Score</option>
                <option value="upside">Max Upside</option>
                <option value="price">Price (Low→High)</option>
              </select>
            </div>
          </div>
        </div>

        {/* State 1: Scanning in Progress */}
        {scanning && (
          <div className="state-panel">
            <div className="state-spinner" />
            <div className="state-title">Scanning Indian Stock Market...</div>
            <div className="state-sub">Fetching ~7,200 NSE & BSE stocks · Computing technical indicators & fundamental metrics · AI scoring</div>
          </div>
        )}
        
        {isAnalyzing && !scanning && (
          <div className="state-panel" style={{ padding: '24px' }}>
            <div className="state-spinner" style={{ width: '30px', height: '30px', marginBottom: '16px' }} />
            <div className="state-title" style={{ fontSize: '18px' }}>Analyzing stock on demand...</div>
          </div>
        )}

        {/* State 2: No Live Scan Done Yet */}
        {!scanning && !isAnalyzing && !hasScanned && onDemandStocks.length === 0 && (
          <div className="state-panel">
            <div className="state-icon">📡</div>
            <div className="state-title">No Live Market Scan Results Available</div>
            <div className="state-sub">
              Select your price range, exchange, and minimum AI score on the left sidebar, then click <strong>"Run Live Scan → Top 20"</strong> to perform a live scan of all ~7,200 Indian market stocks. Or search for a specific stock above.
            </div>
            <button className="scan-btn" style={{ width: 'auto', padding: '12px 24px', marginTop: '12px' }} onClick={onScan}>
              Run Live Market Scan Now
            </button>
          </div>
        )}

        {/* State 3: Scan complete but 0 results match current filters */}
        {!scanning && !isAnalyzing && hasScanned && combinedDisplay.length === 0 && (
          <div className="state-panel">
            <div className="state-title">No recommendations match the active filter criteria</div>
            <div className="state-sub">Try widening your price range or lowering the minimum AI score in the sidebar, or search for a specific stock above.</div>
          </div>
        )}

        {/* State 4: Cards Grid */}
        {!scanning && combinedDisplay.length > 0 && (
          <div className="cards-grid">
            {combinedDisplay.map(stock => (
              <StockCard
                key={stock.ticker}
                stock={stock}
                onSelectWhy={onSelectWhy}
                onOpenAlertModal={onOpenAlertModal}
              />
            ))}
          </div>
        )}
      </main>

      {/* Why Modal */}
      {selectedWhyStock && (
        <WhyModal stock={selectedWhyStock} onClose={onCloseWhyModal} />
      )}
    </div>
  );
}
