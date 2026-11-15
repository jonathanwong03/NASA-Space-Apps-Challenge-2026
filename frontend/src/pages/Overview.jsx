import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api.js'
import {
  ErrorBox, Loading, PHASES, PILLARS, ScenarioSelect, Stat, StatusBadge, useAsync,
} from '../components/ui.jsx'

export default function Overview() {
  const stats = useAsync(() => api.stats(), [])
  const gaps = useAsync(() => api.gaps(), [])
  const habitats = useAsync(() => api.habitats(), [])
  const incidents = useAsync(() => api.incidents(), [])
  const [scenario, setScenario] = useState('lunar_base')
  const recs = useAsync(() => api.recommendations(scenario), [scenario])

  const s = stats.data
  return (
    <>
      <div className="hero">
        <div className="eyebrow">NASA Space Apps 2026 · Fire safety for human exploration</div>
        <h1 className="hero-title">From microgravity flames to safer Moon bases</h1>
        <p>
          FireSafe-SI pulls every combustion-science investigation from NASA's Physical Sciences Informatics (PSI)
          database, extracts the test conditions, and ranks and interprets the findings for spacecraft, stations,
          lunar habitats, rovers and Mars.
        </p>
      </div>

      {stats.error && <ErrorBox error={stats.error} />}
      <div className="grid g4" style={{ marginBottom: 16 }}>
        <Stat label="PSI combustion investigations" value={s ? s.investigations : '…'} note={s && `${s.flight} with flight data`} />
        <Stat label="Test records extracted" value={s ? s.test_rows : '…'} note={s && `from ${s.tables} experimental tables`} />
        <Stat label="Highest O2 tested in microgravity" value={s ? `${s.max_o2.value}%` : '…'} note={s && `${s.max_o2.label}, gaseous fuel`} />
        <Stat label="Highest O2 for solid materials" value={s ? `${s.solid_max_o2}%` : '…'} note="Moon Base target is ≥ 30% O2" />
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <section className="card">
          <div className="card-head">
            <h2>What the data says (and doesn't)</h2>
            <Link to="/coverage" className="small">Coverage map →</Link>
          </div>
          {gaps.loading ? <Loading lines={6} /> : gaps.error ? <ErrorBox error={gaps.error} /> : (
            <div className="stack">
              {gaps.data.findings.map((f, i) => (
                <div key={i} className={`finding ${f.severity}`}>
                  <StatusBadge severity={f.severity} />
                  <h4>{f.title}</h4>
                  <p>{f.detail}</p>
                  {f.investigations.length > 0 && <div className="small muted">Evidence: {f.investigations.join(', ')}</div>}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="card">
          <div className="card-head">
            <h2>Where to look first</h2>
            <ScenarioSelect habitats={habitats.data} value={scenario} onChange={setScenario} label="" />
          </div>
          <p className="small muted">Top investigations per fire-safety pillar for the selected habitat, from the explainable ranking model.</p>
          {recs.loading ? <Loading lines={6} /> : recs.error ? <ErrorBox error={recs.error} /> : (
            <div className="stack">
              {Object.entries(recs.data).map(([pillar, items]) => (
                <div key={pillar}>
                  <h3 style={{ marginBottom: 6 }}>{PILLARS[pillar].icon} {PILLARS[pillar].label} <span className="muted small">· {PILLARS[pillar].blurb}</span></h3>
                  {items.map((r) => (
                    <div key={r.accession} className="row between" style={{ padding: '5px 0', borderBottom: '1px solid var(--border)' }}>
                      <Link to={`/investigations/${r.accession}`} style={{ minWidth: 0 }}>
                        <b>{r.label}</b> <span className="muted small">{r.accession}</span>
                        <div className="small secondary" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 420 }}>{r.summary}</div>
                      </Link>
                      <span className="mono">{r.score.toFixed(0)}</span>
                    </div>
                  ))}
                </div>
              ))}
              <Link to={`/rank?scenario=${scenario}`} className="small">Full ranking with score breakdown →</Link>
            </div>
          )}
        </section>
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <section className="card">
          <div className="card-head"><h2>Investigation timeline</h2><span className="card-sub">PSI start–end years</span></div>
          {s ? <Timeline items={s.timeline} /> : <Loading lines={8} />}
        </section>
        <section className="card">
          <div className="card-head"><h2>Coverage by pillar and fuel</h2><span className="card-sub">investigations (pillar weight ≥ 0.5)</span></div>
          {s ? (
            <>
              {Object.entries(s.pillars).map(([k, v]) => (
                <HBar key={k} label={`${PILLARS[k].icon} ${PILLARS[k].label}`} value={v} max={s.investigations} />
              ))}
              <hr className="divider" />
              {Object.entries(PHASES).map(([k, p]) => (
                <HBar key={k} label={p.label} value={s.phases[k] || 0} max={s.investigations} color={p.color} />
              ))}
              <hr className="divider" />
              <div className="small muted">Hardware families</div>
              {Object.entries(s.hardware).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
                <HBar key={k} label={k} value={v} max={s.investigations} small />
              ))}
            </>
          ) : <Loading lines={8} />}
        </section>
      </div>

      <section className="card">
        <div className="card-head"><h2>Why it matters: fires and oxygen incidents in human spaceflight</h2></div>
        {incidents.data ? incidents.data.map((x) => (
          <div key={x.slug} className="incident">
            <div className="yr">{x.year}</div>
            <div>
              <div className="row between"><b>{x.name}</b><a className="small" href={x.source_url} target="_blank" rel="noreferrer">source ↗</a></div>
              <div className="small muted">{x.vehicle} · {x.atmosphere}</div>
              <p className="secondary small" style={{ margin: '6px 0' }}>{x.cause} {x.outcome}</p>
              <div className="row small">
                {x.pillars.map((p) => <span key={p} className="tag">{PILLARS[p]?.icon} {PILLARS[p]?.label}</span>)}
                {x.related_investigations.length > 0 && <span className="muted">Relevant PSI data:</span>}
                {x.related_investigations.map((a) => <Link key={a} to={`/investigations/${a}`}>{a}</Link>)}
              </div>
            </div>
          </div>
        )) : <Loading />}
      </section>
    </>
  )
}

function HBar({ label, value, max, color, small }) {
  return (
    <div className="comp-row" style={{ gridTemplateColumns: small ? '1fr 120px 24px' : '170px 1fr 28px', marginBottom: 6 }}>
      <span className={small ? 'small secondary' : ''}>{label}</span>
      <div className="bar-track"><div className="bar-fill" style={{ width: `${(value / max) * 100}%`, background: color }} /></div>
      <span className="mono" style={{ textAlign: 'right' }}>{value}</span>
    </div>
  )
}

function Timeline({ items }) {
  const y0 = Math.min(...items.map((i) => i.start))
  const y1 = Math.max(...items.map((i) => i.end || i.start)) + 1
  const x = (y) => ((y - y0) / (y1 - y0)) * 100
  const ticks = []
  for (let y = Math.ceil(y0 / 5) * 5; y <= y1; y += 5) ticks.push(y)
  return (
    <div>
      <div className="legend">
        {Object.entries(PHASES).map(([k, p]) => <span key={k}><span className="dot" style={{ background: p.color }} />{p.label}</span>)}
      </div>
      {items.map((i) => (
        <div className="timeline-row" key={i.accession}>
          <Link to={`/investigations/${i.accession}`} className="small" style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{i.label}</Link>
          <div className="timeline-track">
            <div className="timeline-bar" title={`${i.label}: ${i.start}–${i.end}`}
                 style={{ left: `${x(i.start)}%`, width: `${Math.max(x((i.end || i.start) + 1) - x(i.start), 1)}%`, background: PHASES[i.phase]?.color || 'var(--text-muted)' }} />
          </div>
        </div>
      ))}
      <div className="timeline-row"><span /><div className="axis-ticks" style={{ position: 'relative', display: 'block', height: 14 }}>
        {ticks.map((t) => <span key={t} style={{ position: 'absolute', left: `${x(t)}%`, transform: 'translateX(-50%)' }}>{t}</span>)}
      </div></div>
    </div>
  )
}
