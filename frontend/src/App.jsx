import { Suspense, lazy, useEffect } from 'react'
import { NavLink, Route, Routes, useLocation } from 'react-router-dom'
import { api } from './api.js'
import { ErrorBoundary, Loading, ThemeToggle, useAsync, useTheme } from './components/ui.jsx'
import CommandPalette from './components/CommandPalette.jsx'
const Overview = lazy(() => import('./pages/Overview.jsx'))
const Explorer = lazy(() => import('./pages/Explorer.jsx'))
const InvestigationDetail = lazy(() => import('./pages/InvestigationDetail.jsx'))
const Ranking = lazy(() => import('./pages/Ranking.jsx'))
const Coverage = lazy(() => import('./pages/Coverage.jsx'))
const Compare = lazy(() => import('./pages/Compare.jsx'))
const Ask = lazy(() => import('./pages/Ask.jsx'))
const DataLab = lazy(() => import('./pages/DataLab.jsx'))
const EarthBenefits = lazy(() => import('./pages/EarthBenefits.jsx'))
const Sources = lazy(() => import('./pages/Sources.jsx'))

const NAV = [
  { section: 'Mission' },
  { to: '/', label: 'Overview', ico: '◎', end: true },
  { to: '/rank', label: 'Scenario Ranking', ico: '▤' },
  { to: '/coverage', label: 'Atmosphere Coverage', ico: '◫' },
  { to: '/ask', label: 'Ask the SI', ico: '✦' },
  { section: 'Data' },
  { to: '/investigations', label: 'Investigations', ico: '☰' },
  { to: '/compare', label: 'Compare', ico: '⇄' },
  { to: '/datalab', label: 'Data Lab', ico: '⌁' },
  { section: 'Context' },
  { to: '/earth', label: 'Earth Benefits', ico: '◍' },
  { to: '/sources', label: 'Data Sources & Sync', ico: '⟳' },
]

export default function App() {
  const status = useAsync(() => api.ingestStatus(), [])
  const si = useAsync(() => api.insightsStatus(), [])
  const location = useLocation()
  const [theme, toggleTheme] = useTheme()
  useEffect(() => { window.scrollTo({ top: 0 }) }, [location.pathname])
  const active = NAV.find((n) => n.to && (n.end ? location.pathname === n.to : location.pathname.startsWith(n.to) && n.to !== '/'))
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 64 64" width="20" height="20">
              <path d="M32 13c7 7 11 12 11 20a11 11 0 0 1-22 0c0-4 2-7 4-9 0 3 2 5 4 5 2 0 3-2 2-5-1-3-1-6-1-16z" fill="#fff" />
            </svg>
          </div>
          <div>
            <div className="brand-name">FireSafe-SI</div>
            <div className="brand-sub">Microgravity combustion intelligence</div>
          </div>
        </div>
        <nav className="nav" aria-label="Main">
          {NAV.map((n, i) => n.section
            ? <div key={i} className="nav-section">{n.section}</div>
            : <NavLink key={n.to} to={n.to} end={n.end}><span className="ico" aria-hidden="true">{n.ico}</span>{n.label}</NavLink>)}
        </nav>
        <div className="sidebar-foot">
          {status.data && (
            <div className="foot-card">
              <div className="foot-metrics">
                <span><b>{status.data.investigations}</b> investigations</span>
                <span><b>{status.data.test_rows}</b> test rows</span>
              </div>
              <div className="foot-line">
                <span className="dot" style={{ background: status.data.data_mode === 'live' ? 'var(--good)' : 'var(--warning)' }} />
                {status.data.data_mode === 'live' ? 'Live NASA PSI API' : 'Bundled PSI snapshot'}{status.data.syncing ? ' · syncing…' : ''}
              </div>
              {si.data && <div className="foot-line">SI: {si.data.engine === 'claude' ? `Claude (${si.data.model})` : 'offline rules'}</div>}
            </div>
          )}
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="crumb">
            <span className="muted">FireSafe-SI</span>
            <span className="muted">/</span>
            <span>{active?.label || 'Overview'}</span>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn sm ghost search-trigger" onClick={() => window.dispatchEvent(new Event('firesafe:palette'))}
                    aria-label="Open command palette">
              <span className="muted">⌕ Search</span><kbd>⌘K</kbd>
            </button>
            {si.data && (
              <span className="tag" title="Answer engine">
                <span className="dot" style={{ background: si.data.engine === 'claude' ? 'var(--good)' : 'var(--text-muted)' }} />
                {si.data.engine === 'claude' ? 'Claude online' : 'Offline SI'}
              </span>
            )}
            <ThemeToggle theme={theme} onToggle={toggleTheme} />
          </div>
        </header>
        <ErrorBoundary resetKey={location.pathname + location.search}>
        <Suspense fallback={<Loading lines={6} card />}>
        <div key={location.pathname} className="route-view">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/rank" element={<Ranking />} />
          <Route path="/coverage" element={<Coverage />} />
          <Route path="/ask" element={<Ask />} />
          <Route path="/investigations" element={<Explorer />} />
          <Route path="/investigations/:acc" element={<InvestigationDetail />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/datalab" element={<DataLab />} />
          <Route path="/earth" element={<EarthBenefits />} />
          <Route path="/sources" element={<Sources />} />
          <Route path="*" element={<div className="card">Page not found.</div>} />
        </Routes>
        </div>
        </Suspense>
        </ErrorBoundary>
      </main>
      <CommandPalette />
    </div>
  )
}
