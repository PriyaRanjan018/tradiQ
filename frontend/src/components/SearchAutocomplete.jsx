import React, { useState, useEffect, useRef } from 'react';

export default function SearchAutocomplete({ onSelectStock }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const wrapperRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setResults(data);
        setIsOpen(true);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  return (
    <div className="search-autocomplete-wrapper" ref={wrapperRef} style={{ position: 'relative', flex: 1, maxWidth: '400px' }}>
      <input
        type="text"
        className="toolbar-search"
        placeholder="Search 7,200+ Indian stocks..."
        value={query}
        onChange={e => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0) setIsOpen(true); }}
        style={{ width: '100%' }}
      />
      {isOpen && (
        <div className="autocomplete-dropdown" style={{
          position: 'absolute', top: '100%', left: 0, right: 0,
          backgroundColor: 'var(--c-panel)', border: '1px solid var(--c-border)',
          borderRadius: '8px', marginTop: '4px', zIndex: 100, maxHeight: '300px', overflowY: 'auto',
          boxShadow: '0 4px 12px rgba(0,0,0,0.5)'
        }}>
          {loading && <div style={{ padding: '12px', color: 'var(--c-text-muted)' }}>Searching...</div>}
          {!loading && results.length === 0 && (
             <div style={{ padding: '12px', color: 'var(--c-text-muted)' }}>No stocks found.</div>
          )}
          {!loading && results.map(r => (
            <div 
              key={r.symbol}
              className="autocomplete-item"
              style={{ padding: '10px 12px', borderBottom: '1px solid var(--c-border)', cursor: 'pointer', display: 'flex', justifyContent: 'space-between' }}
              onClick={() => {
                setIsOpen(false);
                setQuery('');
                onSelectStock(r.symbol);
              }}
              onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--c-hover)'}
              onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
            >
              <div>
                <div style={{ fontWeight: '600', color: 'var(--c-text-main)' }}>{r.symbol}</div>
                <div style={{ fontSize: '12px', color: 'var(--c-text-muted)' }}>{r.name}</div>
              </div>
              <div style={{ fontSize: '12px', color: 'var(--c-text-muted)' }}>{r.exchange}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
