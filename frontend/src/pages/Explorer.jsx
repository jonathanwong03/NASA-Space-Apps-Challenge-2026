import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import {
  ErrorBox, Loading, PHASES, PILLARS, PhaseTag, PillarTag, TierTag, fmtRange, useAsync,
} from '../components/ui.jsx'

export default function Explorer() {
  const [params, setParams] = useSearchParams()
  const [q, setQ] = useState(params.get('q') || '')
  const facets = useAsync(() => api.facets(), [])
  const filters = {
    q: params.get('q') || '', pillar: params.get('pillar') || '', phase: params.get('phase') || '',
    hardware: params.get('hardware') || '', tier: params.get('tier') || '',
  }
  const list = useAsync(() => api.investigations(filters), [params.toString()])
  const [semantic, setSemantic] = useState(null)

  useEffect(() => {
    if (!filters.q) { setSemantic(null); return }
    api.search(filters.q).then(setSemantic, () => setSemantic(null))
  }, [filters.q])

  const set = (k, v) => { const p = new URLSearchParams(params); v ? p.set(k, v) : p.delete(k); setParams(p) }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">NASA PSI · Combustion Science</div>
          <h1>Investigations</h1>
          <p>Every combustion investigation in PSI, tagged by fire-safety pillar, fuel phase and hardware, with its tested conditions pulled from the published test tables.</p>
        </div>
        <Link to="/compare" className="btn">⇄ Compare investigations</Link>
      </div>

      <div className="filters">
        <form onSubmit={(e) => { e.preventDefault(); set('q', q.trim()) }} className="row">
          <label className="field">Search
            <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. extinction, PMMA, soot, smoke" style={{ width: 280 }} />
          </label>
          <button className="btn" type="submit" style={{ alignSelf: 'flex-end' }}>Search</button>
        </form>
        <label className="field">Pillar
          <select value={filters.pillar} onChange={(e) => set('pillar', e.target.value)}>
            <option value="">All</option>
            {Object.entries(PILLARS).map(([k, p]) => <option key={k} value={k}>{p.label}</option>)}
          </select>
        </label>
        <label className="field">Fuel phase
          <select value={filters.phase} onChange={(e) => set('phase', e.target.value)}>
            <option value="">All</option>
            {Object.entries(PHASES).map(([k, p]) => <option key={k} value={k}>{p.label}</option>)}
          </select>
        </label>
        <label className="field">Hardware
          <select value={filters.hardware} onChange={(e) => set('hardware', e.target.value)} style={{ maxWidth: 260 }}>
            <option value="">All</option>
            {(facets.data?.hardware || []).map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </label>
        <label className="field">Relevance
          <select value={filters.tier} onChange={(e) => set('tier', e.target.value)}>
            <option value="">All</option>
            <option value="direct">Direct fire safety</option>
            <option value="supporting">Supporting science</option>
          </select>
        </label>
        {params.toString() && <button className="btn ghost" onClick={() => { setQ(''); setParams({}) }} style={{ alignSelf: 'flex-end' }}>Clear</button>}
      </div>

      {semantic && semantic.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="card-head"><h3>Best text matches for “{filters.q}”</h3><span className="card-sub">BM25 relevance across objectives, hypotheses and approach</span></div>
          <div className="stack">
            {semantic.slice(0, 4).map((s) => (
              <div key={s.accession} className="row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
                <div className="bar-track" style={{ width: 60, marginTop: 6, flex: 'none' }}><div className="bar-fill" style={{ width: `${s.score * 100}%` }} /></div>
                <div><Link to={`/investigations/${s.accession}`}><b>{s.label}</b></Link> <span className="muted small">{s.accession}</span>
                  <div className="small secondary">{s.snippet}</div></div>
              </div>
            ))}
          </div>
        </div>
      )}

      {list.loading ? <Loading lines={8} /> : list.error ? <ErrorBox error={list.error} /> : (
        <>
          <div className="small muted" style={{ marginBottom: 10 }}>{list.data.length} investigations</div>
          <div className="inv-grid">
            {list.data.map((i) => (
              <Link key={i.accession} to={`/investigations/${i.accession}`} className="card inv-card">
                <div className="row between"><span className="acc">{i.accession}</span><TierTag tier={i.tier} /></div>
                <h3>{i.acronym || i.title}</h3>
                {i.acronym && <div className="small muted" style={{ marginTop: -6 }}>{i.title}</div>}
                <div className="sum">{i.summary}</div>
                <div className="row">
                  <PhaseTag phase={i.fuel_phase} />
                  {Object.entries(i.pillars || {}).filter(([, w]) => w >= 0.5).map(([k, w]) => <PillarTag key={k} pillar={k} weight={w} />)}
                </div>
                <dl className="kv">
                  <dt>O2</dt><dd>{fmtRange(i.o2, '%')}</dd>
                  <dt>Pressure</dt><dd>{fmtRange(i.pressure_atm, ' atm')}</dd>
                  <dt>Tests</dt><dd>{i.test_count} rows · {i.publication_count} publications</dd>
                  <dt>Hardware</dt><dd className="small">{i.hardware_family}</dd>
                </dl>
              </Link>
            ))}
          </div>
        </>
      )}
    </>
  )
}
