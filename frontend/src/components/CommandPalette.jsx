import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'

const PAGES = [
  { label: 'Overview', to: '/', hint: 'KPIs, gaps, timeline, incidents', ico: '◎' },
  { label: 'Scenario Ranking', to: '/rank', hint: 'explainable per-habitat scoring', ico: '▤' },
  { label: 'Atmosphere Coverage', to: '/coverage', hint: 'O2 vs pressure map', ico: '◫' },
  { label: 'Ask the SI', to: '/ask', hint: 'cited Q&A over the PSI corpus', ico: '✦' },
  { label: 'Investigations', to: '/investigations', hint: 'browse and filter', ico: '☰' },
  { label: 'Compare', to: '/compare', hint: 'two to four side by side', ico: '⇄' },
  { label: 'Data Lab', to: '/datalab', hint: 'plot and export test tables', ico: '⌁' },
  { label: 'Earth Benefits', to: '/earth', hint: 'NASA spinoffs', ico: '◍' },
  { label: 'Data Sources & Sync', to: '/sources', hint: 'provenance and live sync', ico: '⟳' },
]

/** Cmd/Ctrl-K palette: jump to any page or investigation. Zero-dependency. */
export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(0)
  const [invs, setInvs] = useState([])
  const nav = useNavigate()
  const inputRef = useRef(null)

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setOpen((o) => !o) }
      else if (e.key === 'Escape') setOpen(false)
    }
    const onOpen = () => setOpen(true)
    window.addEventListener('keydown', onKey)
    window.addEventListener('firesafe:palette', onOpen)
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('firesafe:palette', onOpen) }
  }, [])

  useEffect(() => { if (open) { setQ(''); setSel(0); setTimeout(() => inputRef.current?.focus(), 20) } }, [open])
  useEffect(() => { if (open && invs.length === 0) api.investigations().then(setInvs, () => {}) }, [open, invs.length])

  const items = useMemo(() => {
    const term = q.trim().toLowerCase()
    const pages = PAGES.map((p) => ({ ...p, kind: 'page' }))
    const matchedInvs = invs
      .filter((i) => !term || `${i.acronym} ${i.title} ${i.accession} ${i.summary}`.toLowerCase().includes(term))
      .slice(0, term ? 8 : 0)
      .map((i) => ({ label: i.acronym || i.title, hint: `${i.accession} · ${i.title}`, to: `/investigations/${i.accession}`, ico: '🔬', kind: 'inv' }))
    const matchedPages = pages.filter((p) => !term || `${p.label} ${p.hint}`.toLowerCase().includes(term))
    return [...matchedPages, ...matchedInvs]
  }, [q, invs])

  useEffect(() => { setSel((s) => Math.min(s, Math.max(items.length - 1, 0))) }, [items.length])

  if (!open) return null
  const go = (item) => { if (!item) return; nav(item.to); setOpen(false) }
  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSel((s) => Math.min(s + 1, items.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)) }
    else if (e.key === 'Enter') { e.preventDefault(); go(items[sel]) }
  }

  return (
    <div className="palette-overlay" onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)}>
      <div className="palette" role="dialog" aria-label="Command palette" aria-modal="true">
        <div className="palette-input">
          <span className="muted">⌕</span>
          <input ref={inputRef} value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={onKeyDown}
                 placeholder="Jump to a page or investigation…" aria-label="Command search" />
          <kbd>esc</kbd>
        </div>
        <div className="palette-list">
          {items.length === 0 && <div className="palette-empty muted">No matches.</div>}
          {items.map((item, i) => (
            <button key={item.to + item.label} className={`palette-item ${i === sel ? 'on' : ''}`}
                    onMouseEnter={() => setSel(i)} onClick={() => go(item)}>
              <span className="palette-ico" aria-hidden="true">{item.ico}</span>
              <span className="palette-label">{item.label}</span>
              <span className="palette-hint muted">{item.hint}</span>
            </button>
          ))}
        </div>
        <div className="palette-foot muted">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>↵</kbd> open</span>
        </div>
      </div>
    </div>
  )
}
