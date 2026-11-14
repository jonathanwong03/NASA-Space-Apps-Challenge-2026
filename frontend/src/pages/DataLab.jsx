import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api.js'
import { ErrorBox, Loading, useAsync } from '../components/ui.jsx'

// First three categorical slots validate for all-pairs (scatter); the rest folds into "Other".
const GROUP_COLORS = ['#3987e5', '#d95926', '#199e70']
const OTHER = '#8a919c'

const PRESETS = [
  { label: 'FLEX: O2 vs burn time', match: 'FLEX', x: /^O initial/, y: /Burn time/ },
  { label: 'FLEX: O2 vs extinction diameter', match: 'FLEX', x: /^O initial/, y: /extinction diameter/ },
  { label: 'CFI-G inverse: O2 vs adiabatic flame T', match: 'Inverse Flames', x: /^XO2$/, y: /^Tad/ },
  { label: 'SPICE: air rate vs fuel rate', match: 'Spice', x: /Air Rate/, y: /^Fuel Rate \(mg/ },
]

export default function DataLab() {
  const [params, setParams] = useSearchParams()
  const tables = useAsync(() => api.tables(), [])
  const tableId = +(params.get('table') || 0)
  const [x, setX] = useState('')
  const [y, setY] = useState('')
  const [group, setGroup] = useState('')
  const [view, setView] = useState('chart')
  const table = useAsync(() => (tableId ? api.table(tableId) : Promise.resolve(null)), [tableId])

  const numeric = table.data?.columns.filter((c) => c.numeric) || []
  const categorical = table.data?.columns.filter((c) => !c.numeric && c.varied && c.distinct <= 30) || []

  useEffect(() => {
    if (!table.data) return
    // default axes: skip bookkeeping columns (run day, test #, year...) when better ones exist
    const bookkeeping = /\b(day|year|month|date|gmt|test|#|number|sample|session)\b/i
    const varied = table.data.columns.filter((c) => c.numeric && c.varied)
    const physical = varied.filter((c) => !bookkeeping.test(c.name))
    const nums = physical.length >= 2 ? physical : varied.length >= 2 ? varied : table.data.columns.filter((c) => c.numeric)
    const want = params.get('x'), wantY = params.get('y')
    setX(want && nums.some((c) => c.name === want) ? want : nums[0]?.name || '')
    setY(wantY && nums.some((c) => c.name === wantY) ? wantY : nums[1]?.name || nums[0]?.name || '')
    setGroup('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [table.data, params.get('x'), params.get('y')])

  const series = useMemo(() => {
    if (!table.data || !x || !y) return []
    const recs = table.data.records.filter((r) => typeof r[x] === 'number' && typeof r[y] === 'number')
    if (!group) return [{ name: `${y} vs ${x}`, color: GROUP_COLORS[0], data: recs }]
    const counts = {}
    recs.forEach((r) => { counts[r[group] || '—'] = (counts[r[group] || '—'] || 0) + 1 })
    const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k]) => k)
    const out = top.map((k, i) => ({ name: k, color: GROUP_COLORS[i], data: recs.filter((r) => (r[group] || '—') === k) }))
    const rest = recs.filter((r) => !top.includes(r[group] || '—'))
    if (rest.length) out.push({ name: 'Other', color: OTHER, data: rest })
    return out
  }, [table.data, x, y, group])

  const choose = (id) => setParams(id ? { table: id } : {})
  const applyPreset = (p) => {
    const t = tables.data?.find((tb) => tb.name.includes(p.match) || tb.label === p.match)
    if (!t) return
    const xs = t.numeric_columns.find((c) => p.x.test(c)), ys = t.numeric_columns.find((c) => p.y.test(c))
    setParams({ table: t.id, ...(xs && { x: xs }), ...(ys && { y: ys }) })
  }
  const n = series.reduce((a, s) => a + s.data.length, 0)

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Predictive-modeling workbench</div>
          <h1>Data Lab</h1>
          <p>Plot any two numeric columns from a PSI test matrix, split by a categorical variable, and export clean CSV for model calibration and validation.</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="row" style={{ marginBottom: 12 }}>
          <span className="small muted">Quick plots:</span>
          {PRESETS.map((p) => <button key={p.label} className="chip" onClick={() => applyPreset(p)}>{p.label}</button>)}
        </div>
        <div className="filters" style={{ marginBottom: 0 }}>
          <label className="field">Test table
            <select value={tableId || ''} onChange={(e) => choose(e.target.value)} style={{ minWidth: 280 }}>
              <option value="">Choose a table…</option>
              {(tables.data || []).map((t) => <option key={t.id} value={t.id}>{t.label}: {t.name} ({t.row_count} rows)</option>)}
            </select>
          </label>
          {table.data && <>
            <label className="field">X axis
              <select value={x} onChange={(e) => setX(e.target.value)}>{numeric.map((c) => <option key={c.name}>{c.name}</option>)}</select>
            </label>
            <label className="field">Y axis
              <select value={y} onChange={(e) => setY(e.target.value)}>{numeric.map((c) => <option key={c.name}>{c.name}</option>)}</select>
            </label>
            <label className="field">Colour by
              <select value={group} onChange={(e) => setGroup(e.target.value)}>
                <option value="">None</option>
                {categorical.map((c) => <option key={c.name}>{c.name}</option>)}
              </select>
            </label>
            <div className="seg" style={{ alignSelf: 'flex-end' }}>
              <button className={view === 'chart' ? 'on' : ''} onClick={() => setView('chart')}>Chart</button>
              <button className={view === 'table' ? 'on' : ''} onClick={() => setView('table')}>Table</button>
            </div>
            <a className="btn" href={api.tableCsvUrl(tableId)} style={{ alignSelf: 'flex-end' }}>⤓ CSV</a>
          </>}
        </div>
      </div>

      {!tableId ? <div className="notice">Choose a test table or a quick plot to begin. {tables.data && `${tables.data.length} tables from ${new Set(tables.data.map((t) => t.accession)).size} investigations are available.`}</div> :
        table.error ? <ErrorBox error={table.error} /> : table.loading || !table.data ? <Loading lines={10} /> : (
          <section className="card">
            <div className="card-head">
              <h2>{x && y ? `${y} vs ${x}` : table.data.name}</h2>
              <span className="card-sub"><Link to={`/investigations/${table.data.accession}`}>{table.data.accession}</Link> · {table.data.name} · {n} plotted rows</span>
            </div>
            {view === 'table' ? (
              <div className="table-wrap">
                <table className="data">
                  <thead><tr>{table.data.columns.map((c) => <th key={c.name}>{c.name}</th>)}</tr></thead>
                  <tbody>{table.data.rows.map((r, i) => <tr key={i}>{r.map((v, j) => <td key={j} className={table.data.columns[j]?.numeric ? 'num' : ''}>{v}</td>)}</tr>)}</tbody>
                </table>
              </div>
            ) : numeric.length === 0 ? (
              <div className="notice">This is a summary table with no numeric columns to plot. Switch to <b>Table</b> view or download the CSV.</div>
            ) : n === 0 ? <div className="notice">No rows have numeric values for both columns. Try other axes or switch to Table view.</div> : (
              <>
                {series.length > 1 && (
                  <div className="legend">{series.map((s) => <span key={s.name}><span className="dot" style={{ background: s.color }} />{s.name} ({s.data.length})</span>)}</div>
                )}
                <div style={{ height: 440 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <ScatterChart margin={{ top: 10, right: 20, bottom: 34, left: 16 }}>
                      <CartesianGrid stroke="var(--border)" vertical={false} />
                      <XAxis type="number" dataKey={x} name={x} domain={['auto', 'auto']} stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                             label={{ value: x, position: 'bottom', offset: 14, fill: 'var(--text-secondary)', fontSize: 12 }} />
                      <YAxis type="number" dataKey={y} name={y} domain={['auto', 'auto']} stroke="var(--text-muted)" tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                             label={{ value: y, angle: -90, position: 'insideLeft', fill: 'var(--text-secondary)', fontSize: 12 }} />
                      <Tooltip cursor={{ strokeDasharray: '3 3', stroke: 'var(--border-strong)' }} content={<Tip x={x} y={y} group={group} />} />
                      {series.map((s) => <Scatter key={s.name} name={s.name} data={s.data} fill={s.color} stroke="#0b0e14" strokeWidth={1.5} isAnimationActive={false} />)}
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </section>
        )}
    </>
  )
}

function Tip({ active, payload, x, y, group }) {
  if (!active || !payload?.length) return null
  const r = payload[0].payload
  const id = Object.entries(r).find(([k]) => /test|sample|flex|#|id/i.test(k))
  return (
    <div className="chart-tip">
      {id && <div className="t">{id[0]}: {String(id[1])}</div>}
      <div className="mono">{x}: {r[x]}</div>
      <div className="mono">{y}: {r[y]}</div>
      {group && <div>{group}: {String(r[group])}</div>}
    </div>
  )
}
