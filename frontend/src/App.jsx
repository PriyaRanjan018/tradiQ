import React, { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import CreateAlertModal from './components/CreateAlertModal';
import NotificationsDrawer from './components/NotificationsDrawer';

const DEFAULT_FILTERS = {
  priceMin: 10,
  priceMax: 2000,
  exchange: 'ALL',      // 'ALL' | 'NSE' | 'BSE'
  minScore: 60,
  sector:   'ALL',
};

// Pure filter function
function applyFilters(picks, f) {
  const maxPrice = f.priceMax >= 99999 ? Infinity : f.priceMax;
  return picks
    .filter(p => p.current_price >= f.priceMin && p.current_price <= maxPrice)
    .filter(p => f.exchange === 'ALL' ? true : p.exchange === f.exchange)
    .filter(p => f.minScore === 0 ? true : p.ai_score >= f.minScore)
    .filter(p => f.sector === 'ALL' ? true : p.sector === f.sector)
    .map((p, i) => ({ ...p, rank: i + 1 }));
}

export default function App() {
  const [allPicks, setAllPicks] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [hasScanned, setHasScanned] = useState(false);
  const [runDate, setRunDate] = useState(null);
  const [selectedWhyStock, setSelectedWhyStock] = useState(null);
  const [alertModalStock, setAlertModalStock] = useState(null);
  const [showNotificationsDrawer, setShowNotificationsDrawer] = useState(false);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  // Persistent alerts state stored in localStorage
  const [alerts, setAlerts] = useState(() => {
    try {
      const saved = localStorage.getItem('tradiq_alerts');
      return saved ? JSON.parse(saved) : [];
    } catch { return []; }
  });

  // Sync alerts to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('tradiq_alerts', JSON.stringify(alerts));
    } catch (e) { console.error('Failed to save alerts', e); }
  }, [alerts]);

  // Save new alert
  const handleSaveAlert = (newAlert) => {
    setAlerts(prev => [newAlert, ...prev]);
  };

  // Delete alert
  const handleDeleteAlert = (alertId) => {
    setAlerts(prev => prev.filter(a => a.id !== alertId));
  };

  // Clear all alerts
  const handleClearAllAlerts = () => {
    if (window.confirm('Are you sure you want to clear all price alerts?')) {
      setAlerts([]);
    }
  };

  // Fetch latest scan results from backend on page load
  const fetchLatestPicks = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/picks/latest`);
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setAllPicks(data);
          setHasScanned(true);
          setRunDate(data[0].run_date || 'Previous Scan');
        }
      }
    } catch (err) {
      console.log('No prior scan report found on server:', err);
    }
  };

  useEffect(() => {
    fetchLatestPicks();
  }, []);

  // Compute available sectors dynamically from loaded picks
  const sectors = useMemo(() => {
    if (!allPicks || allPicks.length === 0) return ['ALL'];
    const set = new Set(allPicks.map(p => p.sector).filter(Boolean));
    return ['ALL', ...Array.from(set).sort()];
  }, [allPicks]);

  // Reactive filtered picks
  const displayedPicks = useMemo(() => applyFilters(allPicks, filters), [allPicks, filters]);

  // Trigger live scan on backend (server is always awake via keep-alive pings)
  const handleScan = async () => {
    setScanning(true);
    try {
      const params = new URLSearchParams({
        price_min: filters.priceMin,
        price_max: filters.priceMax >= 99999 ? 99999 : filters.priceMax,
        exchange:  filters.exchange,
        min_score: filters.minScore,
        sector:    filters.sector,
        top_n:     20,
      });
      const runRes = await fetch(`${API_BASE}/api/run?${params}`, { method: 'POST' });
      if (!runRes.ok) throw new Error('Backend failed to start scan');

      const poll = setInterval(async () => {
        try {
          const st = await fetch(`${API_BASE}/api/status`);
          if (st.ok) {
            const data = await st.json();
            if (!data.pipeline_running) {
              clearInterval(poll);
              const picksRes = await fetch(`${API_BASE}/api/picks/latest`);
              if (picksRes.ok) {
                const liveData = await picksRes.json();
                if (Array.isArray(liveData) && liveData.length > 0) {
                  setAllPicks(liveData);
                  setHasScanned(true);
                  setRunDate(`Live Scan · ${new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}`);
                }
              }
              setScanning(false);
            }
          }
        } catch (e) {
          clearInterval(poll);
          setScanning(false);
        }
      }, 3000);
    } catch (err) {
      console.error('Scan error:', err);
      setScanning(false);
    }
  };

  return (
    <div className="app-root">
      <Header
        scanning={scanning}
        runDate={runDate}
        hasScanned={hasScanned}
        alertCount={alerts.length}
        onToggleNotifications={() => setShowNotificationsDrawer(prev => !prev)}
      />


      <Dashboard
        picks={displayedPicks}
        allPicks={allPicks}
        scanning={scanning}
        hasScanned={hasScanned}
        filters={filters}
        sectors={sectors}
        onFiltersChange={setFilters}
        onScan={handleScan}
        onSelectWhy={setSelectedWhyStock}
        selectedWhyStock={selectedWhyStock}
        onCloseWhyModal={() => setSelectedWhyStock(null)}
        onOpenAlertModal={setAlertModalStock}
      />

      {/* Create Alert Modal */}
      {alertModalStock && (
        <CreateAlertModal
          stock={alertModalStock}
          onClose={() => setAlertModalStock(null)}
          onSaveAlert={handleSaveAlert}
        />
      )}

      {/* Notifications / Alerts Drawer */}
      <NotificationsDrawer
        alerts={alerts}
        isOpen={showNotificationsDrawer}
        onClose={() => setShowNotificationsDrawer(false)}
        onDeleteAlert={handleDeleteAlert}
        onClearAll={handleClearAllAlerts}
      />
    </div>
  );
}
