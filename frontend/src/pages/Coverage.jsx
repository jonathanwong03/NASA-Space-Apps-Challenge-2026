import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CartesianGrid, ReferenceArea, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import { api } from '../api.js'
import { ErrorBox, Loading, PHASES, StatusBadge, useAsync } from '../components/ui.jsx'

const COVERAGE_SEVERITY = { good: 'good', partial: 'warning', none: 'critical' }

export default function Coverage() {
  const cond = useAsync(() => api.conditions(), [])
  const habitats = useAsync(() => api.habitats(), [])
  const gaps = useAsync(() => api.gaps(), [])
  const [selected, setSelected] = useState('lunar_base')
  const [showTable, setShowTable] = useState(false)

  // aggregate identical conditions so overlapping investigations share one mark
  const series = useMemo(() => {
    if (!cond.data) return {}
    const byKey = {}
    for (const c of cond.data) {
      const phase = PHASES[c.phase] ? c.phase : 'aerosol'
      const key = `${phase}|${c.o2}|${c.p_psi}`
      byKey[key] ??= { phase, o2: c.o2, p_psi: c.p_psi, labels: new Set(), assumed: c.assumed }
      byKey[key].labels.add(c.label)
    }
    const out = {}
    for (const v of Object.values(byKey)) {
      (out[v.phase] ??= []).push({ ...v, labels: [...v.labels], n: v.labels.size })
    }
    return out
  }, [cond.data])

  const sel = habitats.data?.find((h) => h.slug === selected)
  const selGap = gaps.data?.scenarios.find((s) => s.slug === selected)

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Flammability envelope</div>
          <h1>Have we tested fires in the air astronauts will breathe?</h1>
          <p>
            Each dot is an oxygen/pressure condition from a PSI test table, coloured by fuel phase. Boxes show the
            atmospheres of crewed environments. Exploration habitats move toward <b>higher O2 at lower pressure</b>,
            and most solid-material flammability data sits outside that region.
          </p>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 2fr) minmax(280px, 1fr)', marginBottom: 16 }}>
        <section className="card">
          <div className="card-head">
            <h2>Tested conditions vs. habitat atmospheres</h2>
            <button className="btn sm ghost" onClick={() => setShowTable((v) => !v)}>{showTable ? 'Show chart' : 'Show table'}</button>
          </div>
          <div className="legend">
            {Object.entries(PHASES).map(([k, p]) => <span key={k}><span className="dot" style={{ background: p.color }} />{p.label}</span>)}
            <span><span style={{ display: 'inline-block', width: 14, height: 10, border: '1.5px dashed var(--brand)' }} />Selected habitat</span>
          </div>
          {cond.loading || habitats.loading ? <Loading lines={10} /> : cond.error ? <ErrorBox error={cond.error} /> : showTable ? (
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th>Fuel phase</th><th>O2 (%)</th><th>Pressure (psi)</th><th>Investigations</th></tr></thead>
                <tbody>
                  {Object.values(series).flat().sort((a, b) => a.o2 - b.o2).map((p, i) => (
                    <tr key={i}><td>{PHASES[p.phase].label}</td><td className="num">{p.o2}</td><td className="num">{p.p_psi}</td><td>{p.labels.join(', ')}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ height: 470 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
                  <CartesianGrid stroke="var(--border)" strokeDasharray="0" vertical={false} />
                  <XAxis type="number" dataKey="o2" name="O2" unit="%" domain={[0, 100]} ticks={[0, 10, 21, 30, 40, 50, 60, 70, 85, 100]}
                         stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                         label={{ value: 'Oxygen concentration (% by volume)', position: 'bottom', offset: 12, fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <YAxis type="number" dataKey="p_psi" name="Pressure" unit=" psi" scale="log" domain={[3, 80]} allowDataOverflow
                         ticks={[4.3, 8.2, 10.2, 14.7, 30, 44, 73]} stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                         label={{ value: 'Pressure (psi, log)', angle: -90, position: 'insideLeft', fill: 'var(--text-secondary)', fontSize: 12 }} />
                  <ZAxis type="number" dataKey="n" range={[60, 260]} />
                  {/* unselected boxes as faint outlines; the selected one drawn last, labelled */}
                  {(habitats.data || []).filter((h) => h.slug !== selected).map((h) => (
                    <ReferenceArea key={h.slug} x1={h.o2_min} x2={h.o2_max} y1={h.p_min_psi} y2={h.p_max_psi}
                      fill="rgba(255,255,255,0.03)" stroke="var(--border-strong)" strokeDasharray="3 3" ifOverflow="extendDomain" />
                  ))}
                  {sel && (
                    <ReferenceArea x1={sel.o2_min} x2={sel.o2_max} y1={sel.p_min_psi} y2={sel.p_max_psi}
                      fill="rgba(252,61,33,0.18)" stroke="var(--brand)" strokeDasharray="5 3" strokeWidth={1.5} ifOverflow="extendDomain"
                      label={{ value: sel.short, position: sel.o2_min > 80 ? 'left' : 'right', fill: 'var(--text-primary)', fontSize: 12, fontWeight: 600 }} />
                  )}
                  <Tooltip cursor={{ strokeDasharray: '3 3', stroke: 'var(--border-strong)' }} content={<PointTip />} />
                  {/* draw order: solids last so the key solid-material evidence is never hidden */}
                  {['gas', 'liquid', 'aerosol', 'solid'].filter((ph) => series[ph]).map((phase) => [phase, series[phase]]).map(([phase, data]) => (
                    <Scatter key={phase} name={PHASES[phase].label} data={data} fill={PHASES[phase].hex}
                             stroke="#0b0e14" strokeWidth={1.5} fillOpacity={0.9} isAnimationActive={false} />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </div>
          )}
          <p className="small muted" style={{ marginTop: 8 }}>
            Where a test table doesn't report O2 or pressure, the ISS cabin value (~21%, ~1 atm) is assumed and the point
            is flagged in the tooltip. Mark size grows with the number of investigations sharing a condition. Faint
            dashed boxes are the other habitats; pick one on the right to highlight it.
          </p>
        </section>

        <aside className="card">
          <h2>Habitat coverage</h2>
          <div className="stack">
            {(gaps.data?.scenarios || []).map((s) => (
              <button key={s.slug} onClick={() => setSelected(s.slug)} className="btn ghost"
                      style={{ justifyContent: 'space-between', borderColor: s.slug === selected ? 'var(--brand)' : undefined, textAlign: 'left' }}>
                <span>{s.name}<br /><span className="small muted">{s.o2_band[0]}–{s.o2_band[1]}% O2 · {s.p_band_psi[0]}–{s.p_band_psi[1]} psi</span></span>
                <StatusBadge severity={COVERAGE_SEVERITY[s.coverage]} />
              </button>
            ))}
          </div>
        </aside>
      </div>

      {sel && selGap && (
        <section className="card">
          <div className="card-head"><h2>{sel.name}: what PSI covers</h2><StatusBadge severity={COVERAGE_SEVERITY[selGap.coverage]} /></div>
          <div className="grid g3">
            <Cell title="Inside the O2 × pressure box" value={`${selGap.points_in_envelope} / ${selGap.total_points}`}
                  note={`tested conditions${selGap.points_near_envelope ? ` · ${selGap.points_near_envelope} more within ${selGap.near_tolerance * 100}% of the boundary` : ''}`}
                  items={selGap.investigations_in_envelope}
                  extra={selGap.investigations_near_envelope.length > 0 && `Near the boundary: ${selGap.investigations_near_envelope.join(', ')}`} />
            <Cell title="O2 range overlaps habitat" value={selGap.investigations_o2_overlap.length}
                  note="investigations (any pressure)" items={selGap.investigations_o2_overlap} />
            <Cell title="Solid-material tests at this O2" value={selGap.solid_material_coverage.length}
                  note="fabrics / plastics flammability" items={selGap.solid_material_coverage} />
          </div>
          <p className="secondary small" style={{ marginTop: 12 }}>{sel.description}</p>
        </section>
      )}
    </>
  )
}

function Cell({ title, value, note, items, extra }) {
  return (
    <div className="card" style={{ background: 'var(--surface-2)' }}>
      <div className="stat-label">{title}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-note">{note}</div>
      <div className="small secondary" style={{ marginTop: 6 }}>{items.length ? items.join(', ') : 'None in PSI'}</div>
      {extra && <div className="small" style={{ marginTop: 4, color: 'var(--text-primary)' }}>{extra}</div>}
    </div>
  )
}

function PointTip({ active, payload }) {
  if (!active || !payload?.length) return null
  const p = payload[0].payload
  return (
    <div className="chart-tip">
      <div className="t">{p.labels.join(', ')}</div>
      <div>{PHASES[p.phase].label}</div>
      <div className="mono">{p.o2}% O2 · {p.p_psi} psi ({(p.p_psi / 14.696).toFixed(2)} atm)</div>
      {p.assumed && <div className="muted">Includes assumed cabin conditions</div>}
    </div>
  )
}
