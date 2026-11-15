import { Fragment, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api.js'
import {
  CopyButton, ErrorBox, Loading, Markdown, PhaseTag, PillarTag, RangeBar, TierTag, fmtRange, useAsync,
} from '../components/ui.jsx'

export default function InvestigationDetail() {
  const { acc } = useParams()
  const inv = useAsync(() => api.investigation(acc), [acc])
  const habitats = useAsync(() => api.habitats(), [])
  const [refresh, setRefresh] = useState(0)
  const brief = useAsync(() => api.brief(acc, refresh > 0), [acc, refresh])
  const [tableIdx, setTableIdx] = useState(0)
  const [showAllPubs, setShowAllPubs] = useState(false)

  if (inv.loading) return <Loading lines={10} />
  if (inv.error) return <ErrorBox error={inv.error} />
  const d = inv.data
  const p = d.profile || {}
  const moon = habitats.data?.find((h) => h.slug === 'lunar_base')
  const table = d.tables[tableIdx]

  return (
    <>
      <div className="page-head">
        <div style={{ minWidth: 0 }}>
          <div className="eyebrow"><Link to="/investigations">Investigations</Link> / {d.accession}</div>
          <h1>{d.acronym ? `${d.acronym}: ` : ''}{d.title}</h1>
          <div className="row" style={{ marginTop: 8 }}>
            <TierTag tier={p.tier} /><PhaseTag phase={p.fuel_phase} />
            {Object.entries(p.pillars || {}).map(([k, w]) => w >= 0.3 && <PillarTag key={k} pillar={k} weight={w} />)}
            {p.partial_gravity_proxy && <span className="tag">Partial-gravity proxy</span>}
          </div>
        </div>
        <div className="row">
          {d.doi && <CopyButton label="Cite" title="Copy DOI citation"
            text={`${d.acronym ? `${d.acronym}: ` : ''}${d.title}. NASA Physical Sciences Informatics, ${d.accession}. https://doi.org/${d.doi}`} />}
          <Link className="btn" to={`/compare?ids=${d.accession}`}>⇄ Compare</Link>
          <a className="btn" href={d.psi_url} target="_blank" rel="noreferrer">Open in NASA PSI ↗</a>
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: 'minmax(0, 1.6fr) minmax(300px, 1fr)', alignItems: 'start' }}>
        <div className="stack" style={{ gap: 16 }}>
          <section className="card">
            <div className="card-head">
              <h2>✦ SI brief</h2>
              <div className="row small muted">
                {brief.data && <span>{brief.data.engine === 'claude' ? `Claude · ${brief.data.model}${brief.data.cached ? ' · cached' : ''}` : 'Offline rule engine'}</span>}
                {brief.data?.engine === 'claude' && <button className="btn sm ghost" onClick={() => setRefresh((n) => n + 1)}>Regenerate</button>}
              </div>
            </div>
            {brief.loading ? <><div className="small muted">Interpreting the investigation…</div><Loading lines={7} /></> :
              brief.error ? <ErrorBox error={brief.error} /> : (
                <>
                  {brief.data.error && <div className="notice" style={{ marginBottom: 10 }}>{brief.data.error}</div>}
                  <Markdown>{brief.data.content}</Markdown>
                </>
              )}
          </section>

          <section className="card">
            <h2>Objective</h2>
            <p className="secondary" style={{ whiteSpace: 'pre-line' }}>{d.objective || '—'}</p>
            {d.hypothesis && <><h3>Hypothesis</h3><p className="secondary" style={{ whiteSpace: 'pre-line' }}>{d.hypothesis}</p></>}
            {d.approach && <><h3>Approach</h3><p className="secondary" style={{ whiteSpace: 'pre-line' }}>{d.approach}</p></>}
          </section>

          {d.tables.length > 0 && (
            <section className="card">
              <div className="card-head">
                <h2>Test matrix</h2>
                <div className="row">
                  {d.tables.length > 1 && (
                    <select value={tableIdx} onChange={(e) => setTableIdx(+e.target.value)}>
                      {d.tables.map((t, i) => <option key={t.id} value={i}>{t.name}</option>)}
                    </select>
                  )}
                  <Link className="btn sm" to={`/datalab?table=${table.id}`}>Plot in Data Lab</Link>
                  <a className="btn sm" href={api.tableCsvUrl(table.id)}>⤓ CSV</a>
                </div>
              </div>
              <TablePreview id={table.id} />
            </section>
          )}

          <section className="card">
            <div className="card-head"><h2>Publications</h2><span className="card-sub">{d.publications.length} listed in PSI</span></div>
            <ol style={{ paddingLeft: 18, margin: 0 }}>
              {(showAllPubs ? d.publications : d.publications.slice(0, 8)).map((pub, i) => (
                <li key={i} style={{ marginBottom: 6 }}>
                  <span>{pub.title}</span>
                  <div className="small muted">{pub.authors}{pub.doi && <> · <a href={`https://doi.org/${pub.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')}`} target="_blank" rel="noreferrer">doi:{pub.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//, '')}</a></>}</div>
                </li>
              ))}
            </ol>
            {d.publications.length > 8 && <button className="btn sm ghost" onClick={() => setShowAllPubs((v) => !v)}>{showAllPubs ? 'Show fewer' : `Show all ${d.publications.length}`}</button>}
          </section>
        </div>

        <div className="stack" style={{ gap: 16 }}>
          {d.thumbnail_url && <img className="thumb" src={d.thumbnail_url} alt={`${d.acronym || d.accession} representative image from NASA PSI`} onError={(e) => { e.currentTarget.style.display = 'none' }} />}
          <section className="card">
            <h2>Test conditions</h2>
            <p className="small muted">Bars show the tested range; the shaded band is the Moon Base target.</p>
            <div className="stack">
              <div><div className="row between small"><span>Oxygen</span><b>{fmtRange(p.o2, '%')}</b></div>
                <RangeBar range={p.o2} domain={[0, 100]} band={moon && [moon.o2_min, moon.o2_max]} />
                <div className="axis-ticks"><span>0%</span><span>50%</span><span>100%</span></div></div>
              <div><div className="row between small"><span>Pressure</span><b>{fmtRange(p.pressure_atm, ' psi', 14.696)}</b></div>
                <RangeBar range={p.pressure_atm} scale={14.696} domain={[3, 80]} log band={moon && [moon.p_min_psi, moon.p_max_psi]} />
                <div className="axis-ticks"><span>3 psi</span><span>14.7</span><span>80 psi</span></div></div>
              <div><div className="row between small"><span>Imposed flow</span><b>{fmtRange(p.flow_cm_s, ' cm/s')}</b></div></div>
            </div>
            {p.assumptions?.length > 0 && <div className="notice small" style={{ marginTop: 10 }}>{p.assumptions.join('. ')}.</div>}
            <hr className="divider" />
            <dl className="kv">
              <dt>Fuels / samples</dt><dd>{p.fuels?.join(', ') || '—'}</dd>
              <dt>Geometry</dt><dd>{p.geometry || '—'}</dd>
              <dt>Measurements</dt><dd>{p.measurements?.join(', ') || '—'}</dd>
              <dt>Test records</dt><dd>{p.test_count}</dd>
            </dl>
          </section>

          <section className="card">
            <h2>How tests differed</h2>
            <h3 className="small muted" style={{ fontWeight: 600 }}>Varied between tests</h3>
            <dl className="kv small">
              {Object.entries(p.variables || {}).slice(0, 14).map(([k, v]) => (
                <Fragment key={k}><dt>{k}</dt><dd>{Array.isArray(v) && typeof v[0] === 'number' ? `${v[0]} – ${v[1]}` : [].concat(v).join(', ')}</dd></Fragment>
              ))}
            </dl>
            <h3 className="small muted" style={{ fontWeight: 600, marginTop: 12 }}>Held constant</h3>
            <dl className="kv small">
              {Object.entries(p.constants || {}).slice(0, 10).map(([k, v]) => <Fragment key={k}><dt>{k}</dt><dd>{v}</dd></Fragment>)}
            </dl>
            {!Object.keys(p.variables || {}).length && <p className="small muted">No test table published.</p>}
          </section>

          <section className="card">
            <h2>Facts</h2>
            <dl className="kv small">
              <dt>Platform</dt><dd>{d.flight_platform || '—'}</dd>
              <dt>Project type</dt><dd>{d.project_type}</dd>
              <dt>Hardware</dt><dd>{d.hardware_link ? <a href={d.hardware_link.split(/\s+/)[0]} target="_blank" rel="noreferrer">{d.hardware || p.hardware_family}</a> : (d.hardware || p.hardware_family)}</dd>
              <dt>Dates</dt><dd>{d.start_date || '?'} → {d.end_date || '?'}</dd>
              <dt>NASA center</dt><dd>{d.managing_center}</dd>
              <dt>DOI</dt><dd>{d.doi ? <a href={`https://doi.org/${d.doi}`} target="_blank" rel="noreferrer">{d.doi}</a> : '—'}</dd>
              <dt>Related</dt><dd>{d.related.length ? d.related.map((r) => <Link key={r} to={`/investigations/${r}`} style={{ marginRight: 8 }}>{r}</Link>) : '—'}</dd>
              <dt>Team</dt><dd>{d.contacts.map((c) => `${c.name}${c.role ? ` (${c.role})` : ''}`).join('; ') || '—'}</dd>
              <dt>Data source</dt><dd>{d.source === 'live' ? 'Live NASA PSI API' : 'Bundled PSI snapshot'}</dd>
            </dl>
          </section>

          {d.research_impacts && (
            <section className="card">
              <h2>◍ Earth benefits</h2>
              <p className="secondary small" style={{ whiteSpace: 'pre-line' }}>{d.research_impacts}</p>
            </section>
          )}
        </div>
      </div>
    </>
  )
}

function TablePreview({ id }) {
  const t = useAsync(() => api.table(id), [id])
  if (t.loading) return <Loading lines={5} />
  if (t.error) return <ErrorBox error={t.error} />
  const cols = t.data.columns
  return (
    <>
      <div className="small muted" style={{ marginBottom: 6 }}>{t.data.rows.length} rows · {cols.length} columns · numeric columns right-aligned</div>
      <div className="table-wrap" style={{ maxHeight: 380 }}>
        <table className="data">
          <thead><tr>{cols.map((c) => <th key={c.name} title={c.varied ? 'varied between tests' : 'constant'}>{c.name}{!c.varied && <span className="muted"> ·</span>}</th>)}</tr></thead>
          <tbody>
            {t.data.rows.slice(0, 200).map((r, i) => (
              <tr key={i}>{r.map((v, j) => <td key={j} className={cols[j]?.numeric ? 'num' : ''}>{v}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
