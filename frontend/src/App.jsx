import { Suspense, lazy } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import { api } from './api.js'
import { Loading, useAsync } from './components/ui.jsx'
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
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true" />
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
            <div>
              <div><b style={{ color: 'var(--text-secondary)' }}>{status.data.investigations}</b> investigations · <b style={{ color: 'var(--text-secondary)' }}>{status.data.test_rows}</b> test rows</div>
              <div>Data: {status.data.data_mode === 'live' ? 'live NASA PSI API' : 'bundled PSI snapshot'}{status.data.syncing ? ' (syncing…)' : ''}</div>
            </div>
          )}
          {si.data && <div style={{ marginTop: 4 }}>SI engine: {si.data.engine === 'claude' ? `Claude (${si.data.model})` : 'offline rules'}</div>}
        </div>
      </aside>
      <main className="main">
        <Suspense fallback={<Loading lines={6} />}>
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
        </Suspense>
      </main>
    </div>
  )
}
