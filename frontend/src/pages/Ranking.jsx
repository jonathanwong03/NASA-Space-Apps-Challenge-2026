import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import {
  ErrorBox, Loading, PhaseTag, PILLARS, ScenarioSelect, TierTag, fmtRange, useAsync,
} from '../components/ui.jsx'

const COMP_LABELS = {
  pillar: 'Pillar fit', directness: 'Fire-safety focus', oxygen: 'O2 match', pressure: 'Pressure match',
  flow: 'Flow match', fuel: 'Fuel relevance', gravity: 'Gravity relevance', data: 'Data richness',
}

export default function Ranking() {
  const [params, setParams] = useSearchParams()
  const scenario = params.get('scenario') || 'lunar_base'
  const focus = params.get('focus') || 'all'
  const habitats = useAsync(() => api.habitats(), [])
  const res = useAsync(() => api.rank(scenario, focus), [scenario, focus])
  const [open, setOpen] = useState(null)

  const set = (k, v) => { const p = new URLSearchParams(params); p.set(k, v); setParams(p) }
  const hab = res.data?.scenario

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">SI ranking</div>
          <h1>Which investigations matter most for your habitat?</h1>
          <p>
            Every investigation gets a score against the selected crew environment: its atmosphere, gravity and
            ventilation, plus the fire-safety pillar you care about. Each score is a transparent weighted sum.
            Expand a row to see why it ranks where it does.
          </p>
        </div>
      </div>

      <div className="filters">
        <ScenarioSelect habitats={habitats.data} value={scenario} onChange={(v) => set('scenario', v)} />
        <label className="field">Fire-safety focus
          <div className="seg" role="group">
            {['all', 'prevention', 'detection', 'suppression'].map((f) => (
              <button key={f} className={focus === f ? 'on' : ''} onClick={() => set('focus', f)}>
                {f === 'all' ? 'All pillars' : `${PILLARS[f].icon} ${PILLARS[f].label}`}
              </button>
            ))}
          </div>
        </label>
      </div>

      {hab && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div className="row between">
            <h2 style={{ margin: 0 }}>{hab.name}</h2>
            {hab.is_assumption && <span className="tag" title="Planning assumption, not an adopted NASA requirement">planning assumption</span>}
          </div>
          <div className="row" style={{ margin: '10px 0', gap: 22 }}>
            <span><span className="muted">O2</span> <b>{hab.o2_min}–{hab.o2_max}%</b></span>
            <span><span className="muted">Pressure</span> <b>{hab.p_min_psi}–{hab.p_max_psi} psi</b></span>
            <span><span className="muted">Gravity</span> <b>{hab.gravity_g} g</b></span>
            <span><span className="muted">Ventilation</span> <b>{hab.flow_min}–{hab.flow_max} cm/s</b></span>
          </div>
          <p className="secondary small" style={{ margin: 0 }}>{hab.description} <span className="muted">Basis: {hab.basis}</span></p>
        </div>
      )}

      <section className="card">
        {res.loading ? <Loading lines={10} /> : res.error ? <ErrorBox error={res.error} /> : (
          <>
            <div className="row between small muted" style={{ paddingBottom: 6, borderBottom: '1px solid var(--border)' }}>
              <span>Weights: {Object.entries(res.data.weights).map(([k, v]) => `${COMP_LABELS[k]} ${(v * 100).toFixed(0)}%`).join(' · ')}</span>
            </div>
            {res.data.results.map((r) => (
              <div key={r.accession} className="rank-item" onClick={() => setOpen(open === r.accession ? null : r.accession)}
                   role="button" tabIndex={0} aria-expanded={open === r.accession}
                   onKeyDown={(e) => e.key === 'Enter' && setOpen(open === r.accession ? null : r.accession)}>
                <div className="rank-num">{r.rank}</div>
                <div style={{ minWidth: 0 }}>
                  <div className="row">
                    <b>{r.label}</b><span className="mono muted">{r.accession}</span>
                    <PhaseTag phase={r.fuel_phase} /><TierTag tier={r.tier} />
                  </div>
                  <div className="small secondary" style={{ marginTop: 3 }}>{r.summary || r.title}</div>
                  <div className="small muted" style={{ marginTop: 2 }}>O2 {fmtRange(r.o2, '%')} · pressure {fmtRange(r.pressure_atm, ' psi', 14.696)}</div>
                </div>
                <div className="rank-score">
                  <div className="bar-track"><div className="bar-fill" style={{ width: `${r.score}%` }} /></div>
                  <b>{r.score.toFixed(0)}</b>
                </div>
                {open === r.accession && (
                  <div className="breakdown" onClick={(e) => e.stopPropagation()}>
                    <div>
                      <div className="small muted" style={{ marginBottom: 6 }}>Score components (contribution to 100)</div>
                      {Object.entries(r.weighted).map(([k, v]) => (
                        <div key={k} className="comp-row" style={{ marginBottom: 5 }}>
                          <span className="secondary">{COMP_LABELS[k]}</span>
                          <div className="bar-track"><div className="bar-fill" style={{ width: `${r.components[k] * 100}%`, opacity: 0.85 }} /></div>
                          <span className="mono" style={{ textAlign: 'right' }}>{v.toFixed(1)}</span>
                        </div>
                      ))}
                    </div>
                    <div>
                      <div className="small muted" style={{ marginBottom: 6 }}>Why</div>
                      <ul className="reasons">{r.reasons.map((x, i) => <li key={i}>{x}</li>)}</ul>
                      <Link to={`/investigations/${r.accession}`} className="small">Open investigation →</Link>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </>
        )}
      </section>
    </>
  )
}
