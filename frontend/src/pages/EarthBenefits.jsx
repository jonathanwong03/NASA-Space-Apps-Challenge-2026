import { Link } from 'react-router-dom'
import { api } from '../api.js'
import { ErrorBox, Loading, PILLARS, useAsync } from '../components/ui.jsx'

export default function EarthBenefits() {
  const spinoffs = useAsync(() => api.spinoffs(), [])
  const invs = useAsync(() => api.investigations({ tier: 'direct' }), [])

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Spinoffs & terrestrial impact</div>
          <h1>Fire safety on Earth</h1>
          <p>
            Without buoyancy, flames expose the basic physics of burning. That knowledge, and the hardware built to
            study it, has improved smoke detectors, extinguishers and firefighter gear on Earth.
          </p>
        </div>
      </div>

      <h2>NASA Spinoffs</h2>
      {spinoffs.loading ? <Loading /> : spinoffs.error ? <ErrorBox error={spinoffs.error} /> : (
        <div className="grid g2" style={{ marginBottom: 24 }}>
          {spinoffs.data.map((s) => (
            <article key={s.slug} className="card">
              <div className="row between"><span className="tag">{PILLARS[s.pillar]?.icon} {PILLARS[s.pillar]?.label}</span><span className="mono muted">{s.year}</span></div>
              <h3 style={{ marginTop: 10 }}>{s.title}</h3>
              <p className="small muted">{s.origin}</p>
              <p className="secondary">{s.application}</p>
              <div className="row small">
                <a href={s.source_url} target="_blank" rel="noreferrer">NASA Spinoff ↗</a>
                {s.related_investigations.length > 0 && <span className="muted">Related PSI research:</span>}
                {s.related_investigations.map((a) => <Link key={a} to={`/investigations/${a}`}>{a}</Link>)}
              </div>
            </article>
          ))}
        </div>
      )}

      <h2>Earth benefits stated by the investigators</h2>
      <p className="secondary small">From the "Research Impacts / Earth Benefits" field of each fire-safety investigation in PSI.</p>
      {invs.loading ? <Loading /> : invs.error ? <ErrorBox error={invs.error} /> : (
        <div className="inv-grid">
          {invs.data.map((i) => <ImpactCard key={i.accession} acc={i.accession} label={i.acronym || i.accession} />)}
        </div>
      )}
    </>
  )
}

function ImpactCard({ acc, label }) {
  const d = useAsync(() => api.investigation(acc), [acc])
  return (
    <div className="card">
      <div className="row between"><Link to={`/investigations/${acc}`}><b>{label}</b></Link><span className="mono muted small">{acc}</span></div>
      {d.loading ? <Loading lines={2} /> : <p className="small secondary" style={{ marginTop: 8 }}>{(d.data?.research_impacts || 'Not stated.').slice(0, 420)}{(d.data?.research_impacts || '').length > 420 ? '…' : ''}</p>}
    </div>
  )
}
