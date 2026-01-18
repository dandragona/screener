import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

function App() {
  const [tickers, setTickers] = useState([])
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [analyzingSymbol, setAnalyzingSymbol] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisCache, setAnalysisCache] = useState({})

  const handleAnalyze = async (symbol) => {
    setAnalyzingSymbol(symbol)

    // Check cache first
    if (analysisCache[symbol]) {
      setAnalysisResult(analysisCache[symbol])
      setAnalyzingSymbol(null)
      return
    }

    try {
      const response = await fetch(`http://localhost:8000/analyze/${symbol}`)
      if (!response.ok) throw new Error('Analysis failed')
      const data = await response.json()
      setAnalysisResult(data)
      // Update cache
      setAnalysisCache(prev => ({ ...prev, [symbol]: data }))
    } catch (err) {
      console.error(err)
      alert('Failed to generate analysis')
    } finally {
      setAnalyzingSymbol(null)
    }
  }

  const closeAnalysis = () => {
    setAnalysisResult(null)
  }

  // Default tickers to start with (Empty to trigger backend default/Russell 2000)
  const DEFAULT_INPUT = ""

  const [lastUpdated, setLastUpdated] = useState(null)

  useEffect(() => {
    handleScreen()
  }, [])

  const handleScreen = async (forceRefresh = false) => {
    setLoading(true)
    setError(null)

    try {
      // Check cache unless forcing refresh
      if (!forceRefresh) {
        const cached = localStorage.getItem('screenerResults')
        if (cached) {
          const { data, timestamp } = JSON.parse(cached)
          const now = Date.now()
          // 24 hours in milliseconds
          const ONE_DAY = 24 * 60 * 60 * 1000

          if (now - timestamp < ONE_DAY) {
            setResults(data)
            setLastUpdated(timestamp)
            setLoading(false)
            return
          }
        }
      }

      setResults([])
      // Use default input if tickers state is empty
      const tickerList = tickers.length > 0 ? tickers : (DEFAULT_INPUT ? DEFAULT_INPUT.split(',') : [])
      const query = tickerList.length > 0 ? tickerList.map(t => `tickers=${t.trim()}`).join('&') : ''

      const response = await fetch(`http://localhost:8000/screen?${query}`)
      if (!response.ok) {
        throw new Error('Failed to fetch data')
      }

      const data = await response.json()
      setResults(data)

      // Update cache
      const now = Date.now()
      localStorage.setItem('screenerResults', JSON.stringify({
        data,
        timestamp: now
      }))
      setLastUpdated(now)
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getScoreStyle = (score) => {
    // 0 = red (0deg), 100 = green (120deg)
    const hue = Math.max(0, Math.min(120, (score / 100) * 120))
    return {
      backgroundColor: `hsla(${hue}, 80%, 35%, 0.2)`,
      color: `hsl(${hue}, 80%, 45%)`,
      borderColor: `hsla(${hue}, 80%, 35%, 0.4)`
    }
  }

  return (
    <div className="container">
      <header className="header">
        <div className="header-content">
          <div className="logo">Arc Screener</div>
        </div>
      </header>

      <section className="hero-section">
        <h1 className="hero-title">Growth Curves for the DIY Investor</h1>
        <p className="hero-subtitle">Premium long-term equity monitoring and AI-powered analysis for the modern investor.</p>

        <div className="stats-grid" style={{ maxWidth: '1000px', margin: '0 auto' }}>
          <div className="card stat-card">
            <div className="stat-value">{results.length}</div>
            <div className="stat-label">Tickers Screened</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">
              {results.length > 0 ? Math.max(...results.map(r => r.calculated_metrics?.score || 0)).toFixed(1) : '--'}
            </div>
            <div className="stat-label">Top Score</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">
              {results.length > 0
                ? (results.reduce((acc, r) => acc + (r.calculated_metrics?.p_fcf || 0), 0) / results.filter(r => r.calculated_metrics?.p_fcf).length).toFixed(1)
                : '--'}
            </div>
            <div className="stat-label">Avg P/FCF</div>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: '2rem', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
          <button
            onClick={() => handleScreen(true)}
            disabled={loading}
            style={{
              padding: '10px 24px',
              fontSize: '1rem',
              borderRadius: '8px',
              border: 'none',
              background: 'var(--accent-gradient)',
              color: 'white',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              fontWeight: 600,
              boxShadow: '0 4px 12px rgba(100, 108, 255, 0.3)'
            }}
          >
            {loading ? 'Refreshing...' : 'Refresh Data'}
          </button>

          {lastUpdated && (
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', opacity: 0.8 }}>
              Last updated: {new Date(lastUpdated).toLocaleString()}
            </div>
          )}
        </div>
      </section>

      <div style={{ marginTop: '2rem' }}>
        {error && <div className="card" style={{ color: 'var(--danger-color)', borderColor: 'var(--danger-color)' }}>{error}</div>}

        {results.length > 0 && (
          <div className="card" style={{ background: 'transparent', border: 'none', padding: 0, boxShadow: 'none' }}>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'separate', borderSpacing: '0 12px' }}>
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Price</th>
                    <th>Score</th>
                    <th>P/FCF</th>
                    <th>PEG</th>
                    <th>ROE</th>
                    <th>Debt/Eq</th>
                    <th>HV</th>
                    <th>IV (S)</th>
                    <th>IV Rank</th>
                    <th>IV Ratio</th>
                    <th>Insider</th>
                    <th>Action</th>
                    <th>Target (L, M, H)</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((r) => {
                    const score = r.calculated_metrics?.score || 0
                    const formatPercent = (val) => val ? (val * 100).toFixed(1) + '%' : 'N/A'
                    const formatInsider = (val) => {
                      if (val === null || val === undefined) return 'N/A'
                      const num = Number(val)
                      if (num === 0) return '0'
                      if (Math.abs(num) >= 1000000) return (num / 1000000).toFixed(1) + 'M'
                      if (Math.abs(num) >= 1000) return (num / 1000).toFixed(0) + 'k'
                      return num.toFixed(0)
                    }

                    const getInsiderClass = (val) => {
                      if (val > 0) return 'metric-good'
                      if (val < 0) return 'metric-bad'
                      return 'metric-neutral'
                    }

                    return (
                      <tr key={r.symbol}>
                        <td style={{ fontWeight: '800', color: 'var(--text-inverse)', fontFamily: 'var(--heading-font)' }}>{r.symbol}</td>
                        <td style={{ fontWeight: '600' }}>${r.current_price?.toFixed(2)}</td>
                        <td>
                          <span className="score-badge" style={{
                            ...getScoreStyle(score),
                            padding: '0.4rem 1rem',
                            borderRadius: '10px',
                            fontSize: '0.9rem'
                          }}>
                            {score.toFixed(1)}
                          </span>
                        </td>
                        <td>{r.calculated_metrics?.p_fcf ? r.calculated_metrics.p_fcf.toFixed(1) : 'N/A'}</td>
                        <td>{r.peg_ratio?.toFixed(2) || 'N/A'}</td>
                        <td>{formatPercent(r.return_on_equity)}</td>
                        <td>{r.debt_to_equity?.toFixed(2) || 'N/A'}</td>
                        <td className="metric-neutral">{formatPercent(r.historical_volatility)}</td>
                        <td className="metric-neutral">{formatPercent(r.iv_short)}</td>
                        <td>{r.calculated_metrics?.iv_rank ? (r.calculated_metrics.iv_rank * 100).toFixed(0) + '%' : 'N/A'}</td>
                        <td>{r.iv_term_structure_ratio?.toFixed(2) || 'N/A'}</td>
                        <td className={getInsiderClass(r.insider_net_shares)}>
                          {formatInsider(r.insider_net_shares)}
                        </td>
                        <td>
                          <button
                            className="analyze-btn"
                            onClick={() => handleAnalyze(r.symbol)}
                            disabled={analyzingSymbol === r.symbol}
                            style={{
                              padding: '8px 16px',
                              borderRadius: '8px'
                            }}
                          >
                            {analyzingSymbol === r.symbol ? 'Analyzing...' : 'Analyze'}
                          </button>
                        </td>
                        <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          <span style={{ color: 'var(--text-primary)', fontWeight: '500' }}>
                            ${r.target_mean?.toFixed(0) || 'N/A'}
                          </span>
                          <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                            ${r.target_low?.toFixed(0) || 'N/A'} • ${r.target_high?.toFixed(0) || 'N/A'}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {analysisResult && (
          <div className="modal-overlay" onClick={closeAnalysis}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
              <button className="modal-close" onClick={closeAnalysis}>&times;</button>
              <h3 style={{
                marginTop: 0,
                marginBottom: '2rem',
                fontSize: '2rem',
                fontFamily: 'var(--heading-font)',
                fontWeight: 800,
                background: 'var(--accent-gradient)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent'
              }}>
                Analysis: {analysisResult.symbol}
              </h3>
              <div className="markdown-content">
                <ReactMarkdown>
                  {typeof analysisResult.analysis === 'string' ? analysisResult.analysis : 'No analysis available.'}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {!loading && results.length === 0 && !error && (
          <div className="loading" style={{ padding: '8rem 0' }}>
            <div className="logo" style={{ marginBottom: '1.5rem', opacity: 0.5 }}>Arc Screener</div>
            Fetching latest market intelligence...
          </div>
        )}
      </div>
    </div>
  )
}

export default App
