import { Component, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Link } from 'react-router-dom'

// Fuel phase -> fixed categorical slot (colour follows the entity, never its rank).
export const PHASES = {
  solid: { label: 'Solid materials', color: 'var(--series-1)', hex: '#3987e5' },
  liquid: { label: 'Liquid droplets', color: 'var(--series-2)', hex: '#d95926' },
  gas: { label: 'Gaseous flames', color: 'var(--series-3)', hex: '#199e70' },
  aerosol: { label: 'Smoke / dust aerosol', color: 'var(--series-other)', hex: '#8a919c' },
}

export const PILLARS = {
  prevention: { label: 'Prevention', icon: '🛡️', blurb: 'ignition control & material flammability' },
  detection: { label: 'Detection', icon: '🔎', blurb: 'smoke & aerosol sensing' },
  suppression: { label: 'Suppression', icon: '🧯', blurb: 'extinguishment & dilution' },
}

const STATUS = {
  critical: { color: 'var(--critical)', icon: '!', label: 'Critical gap' },
  serious: { color: 'var(--serious)', icon: '!', label: 'Serious gap' },
  warning: { color: 'var(--warning)', icon: '△', label: 'Limited data' },
  good: { color: 'var(--good)', icon: '✓', label: 'Covered' },
}

/** Theme: 'dark' | 'light', persisted to localStorage and reflected on <html data-theme>. */
export function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('firesafe-theme') || 'dark' } catch { return 'dark' }
  })
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem('firesafe-theme', theme) } catch { /* private mode */ }
  }, [theme])
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))]
}

export function ThemeToggle({ theme, onToggle }) {
  const dark = theme !== 'light'
  return (
    <button className="btn sm ghost icon-btn" onClick={onToggle} title={`Switch to ${dark ? 'light' : 'dark'} mode`}
            aria-label={`Switch to ${dark ? 'light' : 'dark'} mode`}>
      {dark ? '☾' : '☀'}
    </button>
  )
}

export function useAsync(fn, deps = []) {
  const key = JSON.stringify(deps)
  const [state, set] = useState({ data: null, error: null, loading: true, key })
  useEffect(() => {
    let alive = true
    set((s) => ({ ...s, loading: true, error: null, key }))
    fn().then(
      (data) => alive && set({ data, error: null, loading: false, key }),
      (error) => alive && set({ data: null, error, loading: false, key }),
    )
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  // Inputs changed but the effect hasn't run yet: report loading, never a stale "done" result.
  if (state.key !== key) return { data: state.data, error: null, loading: true }
  return state
}

/** Catches render errors so one broken view shows a message instead of blanking the whole app. */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidUpdate(prev) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null })
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="error" role="alert">
        <b>Something went wrong on this page.</b> {String(this.state.error?.message || this.state.error)}
        <div style={{ marginTop: 8 }}><button className="btn sm" onClick={() => this.setState({ error: null })}>Try again</button></div>
      </div>
    )
  }
}

export function Loading({ lines = 3 }) {
  return <div aria-busy="true">{Array.from({ length: lines }, (_, i) => <div key={i} className="skeleton" style={{ width: `${90 - i * 15}%` }} />)}</div>
}

export function ErrorBox({ error }) {
  return <div className="error" role="alert">Could not load data: {String(error?.message || error)}</div>
}

export function PhaseTag({ phase }) {
  const p = PHASES[phase] || { label: phase || 'unknown', color: 'var(--text-muted)' }
  return <span className="tag"><span className="dot" style={{ background: p.color }} />{p.label}</span>
}

export function PillarTag({ pillar, weight }) {
  const p = PILLARS[pillar]
  if (!p) return null
  return <span className="tag" title={p.blurb}>{p.icon} {p.label}{weight != null && <span className="muted">{weight.toFixed(1)}</span>}</span>
}

export function TierTag({ tier }) {
  return tier === 'direct'
    ? <span className="tag direct" title="Explicitly a spacecraft fire-safety investigation">🔥 Direct fire safety</span>
    : <span className="tag" title="Fundamental combustion science that supports fire safety">Supporting science</span>
}

export function StatusBadge({ severity }) {
  const s = STATUS[severity] || STATUS.warning
  return <span className="status" style={{ color: s.color }}><span className="sicon" style={{ background: s.color }}>{s.icon}</span>{s.label}</span>
}

export function Stat({ label, value, note }) {
  return (
    <div className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {note && <div className="stat-note">{note}</div>}
    </div>
  )
}

export function Markdown({ children }) {
  return (
    <div className="md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: c }) => <a href={href} target="_blank" rel="noreferrer">{c}</a>,
          // turn [PSI-69 FLEX] style citations into links
          p: ({ children: c }) => <p>{linkify(c)}</p>,
          li: ({ children: c }) => <li>{linkify(c)}</li>,
        }}
      >
        {children || ''}
      </ReactMarkdown>
    </div>
  )
}

function linkify(children) {
  const walk = (node, k) => {
    if (typeof node !== 'string') return node
    const parts = node.split(/(\[?PSI-\d+[^\]\n]{0,24}\]?)/g)
    return parts.map((part, i) => {
      const m = part.match(/PSI-\d+/)
      if (!m || !/^\[?PSI-\d+/.test(part)) return part
      return <Link key={`${k}-${i}`} to={`/investigations/${m[0]}`}>{part}</Link>
    })
  }
  return Array.isArray(children) ? children.map((c, i) => walk(c, i)) : walk(children, 0)
}

export function fmtRange(r, unit = '', scale = 1, digits = 3) {
  if (!r) return '—'
  const lo = +(r.min * scale).toPrecision(digits)
  const hi = +(r.max * scale).toPrecision(digits)
  return lo === hi ? `${lo}${unit}` : `${lo}–${hi}${unit}`
}

/** Horizontal range bar on a fixed axis, with optional highlighted scenario band. */
export function RangeBar({ range, domain, band, color = 'var(--seq-500)', scale = 1, unit = '', log = false }) {
  const [d0, d1] = domain
  const t = (v) => {
    const c = Math.min(Math.max(v, d0), d1)
    return log ? (Math.log(c / d0) / Math.log(d1 / d0)) * 100 : ((c - d0) / (d1 - d0)) * 100
  }
  return (
    <div>
      <div className="range-track">
        {band && <div className="range-band" style={{ left: `${t(band[0])}%`, width: `${Math.max(t(band[1]) - t(band[0]), 0.8)}%` }} />}
        {range && (
          <div className="range-bar" title={fmtRange(range, unit, scale)}
               style={{ left: `${t(range.min * scale)}%`, width: `${Math.max(t(range.max * scale) - t(range.min * scale), 1.2)}%`, background: color }} />
        )}
      </div>
    </div>
  )
}

export function ScenarioSelect({ habitats, value, onChange, label = 'Habitat scenario' }) {
  return (
    <label className="field">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {(habitats || []).map((h) => <option key={h.slug} value={h.slug}>{h.name}</option>)}
      </select>
    </label>
  )
}
