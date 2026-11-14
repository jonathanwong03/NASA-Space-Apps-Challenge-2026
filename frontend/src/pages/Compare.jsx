import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api.js'
import {
  ErrorBox, Loading, PHASES, PILLARS, PhaseTag, RangeBar, fmtRange, useAsync,
} from '../components/ui.jsx'

const PRESETS = [
  { label: 'Droplet suppression: FLEX vs FLEX-2 vs CFI', ids: ['PSI-69', 'PSI-68', 'PSI-39'] },
  { label: 'Solid flammability: BASS vs BASS-II vs Saffire-II', ids: ['PSI-26', 'PSI-25', 'PSI-99'] },
  { label: 'Smoke & dust: SAME vs SAME-R vs DAFT', ids: ['PSI-102', 'PSI-101', 'PSI-47'] },
  { label: 'ACME gaseous flames: BRE vs CFI-G vs E-FIELD', ids: ['PSI-20', 'PSI-159', 'PSI-22'] },
]

export default function Compare() {
  const [params, setParams] = useSearchParams()
  const ids = (params.get('ids') || '').split(',').filter(Boolean)
  const all = useAsync(() => api.investigations(), [])
  const habitats = useAsync(() => api.habitats(), [])
  const cmp = useAsync(() => (ids.length >= 2 ? api.compare(ids) : Promise.resolve(null)), [ids.join(',')])
  const moon = habitats.data?.find((h) => h.slug === 'lunar_base')

  const setIds = (next) => setParams(next.length ? { ids: next.join(',') } : {})
  const toggle = (acc) => setIds(ids.includes(acc) ? ids.filter((x) => x !== acc) : [...ids, acc].slice(-4))

  const items = cmp.data?.items || []
  const rows = [
    ['Fuel phase', (i) => <PhaseTag phase={i.fuel_phase} />],
    ['Primary pillar', (i) => i.primary_pillar && `${PILLARS[i.primary_pillar].icon} ${PILLARS[i.primary_pillar].label}`],
    ['Hardware', (i) => i.hardware_family],
    ['Platform', (i) => i.flight_platform || '—'],
    ['Sample / burner geometry', (i) => i.geometry || '—'],
    ['Fuels / materials', (i) => i.fuels.slice(0, 6).join(', ') || '—'],
    ['O2', (i) => fmtRange(i.o2, '%')],
    ['Pressure', (i) => fmtRange(i.pressure_atm, ' atm')],
    ['Flow', (i) => fmtRange(i.flow_cm_s, ' cm/s')],
    ['Test records', (i) => i.test_count],
    ['Measurements', (i) => i.measurements.join(', ') || '—'],
    ['Varied parameters', (i) => i.variable_names.slice(0, 8).join(', ') || '—'],
    ['Years', (i) => `${i.start_year || '?'}–${i.end_year || '?'}`],
  ]

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Side by side</div>
          <h1>Compare investigations</h1>
          <p>Pick two to four investigations to line up objectives, fuels, test conditions, sensors and the parameters they varied. Shared and differing attributes are found automatically.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="row" style={{ marginBottom: 10 }}>
          <span className="small muted">Presets:</span>
          {PRESETS.map((p) => <button key={p.label} className="chip" onClick={() => setIds(p.ids)}>{p.label}</button>)}
        </div>
        <div className="chips">
          {(all.data || []).map((i) => (
            <button key={i.accession} className="chip" onClick={() => toggle(i.accession)}
                    style={ids.includes(i.accession) ? { borderColor: 'var(--brand)', color: 'var(--text-primary)', background: 'var(--brand-soft)' } : undefined}
                    aria-pressed={ids.includes(i.accession)}>
              <span className="dot" style={{ background: PHASES[i.fuel_phase]?.color, marginRight: 6 }} />{i.acronym || i.accession}
            </button>
          ))}
        </div>
        <div className="small muted" style={{ marginTop: 8 }}>{ids.length} selected (max 4)</div>
      </div>

      {ids.length < 2 ? <div className="notice">Select at least two investigations, or pick a preset.</div> :
        cmp.loading ? <Loading lines={10} /> : cmp.error ? <ErrorBox error={cmp.error} /> : (
          <>
            <div className="grid g2" style={{ marginBottom: 16 }}>
              <section className="card">
                <h2>✓ What they share</h2>
                {cmp.data.similarities.length ? cmp.data.similarities.map((s, i) => (
                  <div key={i} className="small" style={{ marginBottom: 8 }}>
                    <b>{s.attribute}</b>{s.overlap ? <> overlap <span className="mono">{+s.overlap.min.toPrecision(3)}–{+s.overlap.max.toPrecision(3)}</span></> : ': '}
                    {!s.overlap && <span className="secondary">{Array.isArray(s.values) ? s.values.join(', ') : Object.values(s.values)[0]}</span>}
                  </div>
                )) : <p className="muted small">Nothing in common beyond the PSI combustion program.</p>}
              </section>
              <section className="card">
                <h2>≠ Where they differ</h2>
                {cmp.data.differences.map((s, i) => (
                  <div key={i} className="small" style={{ marginBottom: 8 }}>
                    <b>{s.attribute}</b>
                    <div className="secondary">{Object.entries(s.values).map(([acc, v]) => `${items.find((x) => x.accession === acc)?.label}: ${typeof v === 'object' && v ? `${+v.min.toPrecision(3)}–${+v.max.toPrecision(3)}` : v ?? '—'}`).join(' · ')}</div>
                  </div>
                ))}
              </section>
            </div>

            <section className="card" style={{ marginBottom: 16 }}>
              <div className="card-head"><h2>Tested envelope</h2><span className="card-sub">shaded band = Moon Base target</span></div>
              <div className="grid g2">
                <div>
                  <h3 className="small muted">Oxygen (%)</h3>
                  {items.map((i) => (
                    <div key={i.accession} style={{ marginBottom: 8 }}>
                      <div className="row between small"><span>{i.label}</span><span className="mono">{fmtRange(i.o2, '%')}</span></div>
                      <RangeBar range={i.o2} domain={[0, 100]} band={moon && [moon.o2_min, moon.o2_max]} color={PHASES[i.fuel_phase]?.color} />
                    </div>
                  ))}
                  <div className="axis-ticks"><span>0</span><span>50</span><span>100</span></div>
                </div>
                <div>
                  <h3 className="small muted">Pressure (psi, log scale)</h3>
                  {items.map((i) => (
                    <div key={i.accession} style={{ marginBottom: 8 }}>
                      <div className="row between small"><span>{i.label}</span><span className="mono">{fmtRange(i.pressure_atm, ' psi', 14.696)}</span></div>
                      <RangeBar range={i.pressure_atm} scale={14.696} domain={[3, 80]} log band={moon && [moon.p_min_psi, moon.p_max_psi]} color={PHASES[i.fuel_phase]?.color} />
                    </div>
                  ))}
                  <div className="axis-ticks"><span>3</span><span>14.7</span><span>80</span></div>
                </div>
              </div>
            </section>

            <section className="card">
              <h2>Attribute matrix</h2>
              <div className="table-wrap" style={{ maxHeight: 'none' }}>
                <table className="data">
                  <thead><tr><th style={{ width: 170 }}>Attribute</th>{items.map((i) => <th key={i.accession}><Link to={`/investigations/${i.accession}`}>{i.label}</Link> <span className="muted mono">{i.accession}</span></th>)}</tr></thead>
                  <tbody>
                    <tr><td className="muted">Objective</td>{items.map((i) => <td key={i.accession} className="small secondary">{(i.objective || '').slice(0, 320)}{(i.objective || '').length > 320 ? '…' : ''}</td>)}</tr>
                    {rows.map(([label, fn]) => (
                      <tr key={label}><td className="muted">{label}</td>{items.map((i) => <td key={i.accession}>{fn(i)}</td>)}</tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
    </>
  )
}
