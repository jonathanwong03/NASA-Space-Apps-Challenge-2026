import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, askStream } from '../api.js'
import { Markdown, ScenarioSelect, useAsync } from '../components/ui.jsx'

const SUGGESTIONS = [
  'Which PSI data best predicts how cabin fabrics burn in a 34% O2, 8.2 psi Moon Base atmosphere?',
  'How much CO2 or helium dilution extinguished droplet flames in FLEX, and what does that imply for suppression systems?',
  'What smoke particle sizes did SAME and SAME-R measure, and how should that shape detector design?',
  'Can microgravity and 1 g results bound flame behavior at lunar gravity? What is missing?',
  'Which experimental tables could validate a CFD model of concurrent flame spread over solids?',
  'Compare concurrent vs opposed flow flame spread in the Saffire experiments.',
]

export default function Ask() {
  const habitats = useAsync(() => api.habitats(), [])
  const status = useAsync(() => api.insightsStatus(), [])
  const [scenario, setScenario] = useState('lunar_base')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState([])
  const [busy, setBusy] = useState(false)
  const abort = useRef(null)
  const end = useRef(null)

  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages])

  async function send(text) {
    const question = (text ?? input).trim()
    if (!question || busy) return
    setInput('')
    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((m) => [...m, { role: 'user', content: question }, { role: 'assistant', content: '', streaming: true }])
    setBusy(true)
    abort.current = new AbortController()
    const patch = (fn) => setMessages((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    try {
      await askStream({ question, scenario, history }, (ev) => {
        if (ev.type === 'meta') patch((a) => ({ ...a, sources: ev.sources, engine: ev.engine, model: ev.model }))
        else if (ev.type === 'text') patch((a) => ({ ...a, content: a.content + ev.text }))
      }, abort.current.signal)
    } catch (e) {
      if (e.name !== 'AbortError') patch((a) => ({ ...a, content: `${a.content}\n\n**Error:** ${e.message}` }))
    } finally {
      patch((a) => ({ ...a, streaming: false }))
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Ask the SI</div>
          <h1>Ask questions of NASA's combustion record</h1>
          <p>
            Answers draw on every PSI combustion investigation: objectives, test matrices, extracted conditions and
            publications. They cite their sources and say when the data doesn't cover your scenario.
          </p>
        </div>
      </div>

      <div className="chat">
        <section className="card">
          <div className="chat-log" aria-live="polite">
            {messages.length === 0 && (
              <div className="stack">
                <p className="muted">Try one of these:</p>
                {SUGGESTIONS.map((s) => <button key={s} className="chip" style={{ padding: '8px 12px' }} onClick={() => send(s)}>{s}</button>)}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === 'assistant' && (
                  <div className="msg-meta">
                    <span>✦ {m.engine === 'claude' ? `Claude · ${m.model}` : m.engine ? 'Offline SI engine' : 'Thinking…'}</span>
                    {m.sources?.length > 0 && <span>· retrieved:</span>}
                    {m.sources?.slice(0, 5).map((s) => <Link key={s.accession} to={`/investigations/${s.accession}`} className="tag">{s.label}</Link>)}
                  </div>
                )}
                {m.role === 'user' ? m.content : (
                  <div className={m.streaming ? 'cursor' : ''}><Markdown>{m.content}</Markdown></div>
                )}
              </div>
            ))}
            <div ref={end} />
          </div>
          <form className="composer" onSubmit={(e) => { e.preventDefault(); send() }}>
            <textarea rows={2} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about flammability, detection, suppression, test conditions…"
                      onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} aria-label="Question" />
            {busy ? <button type="button" className="btn" onClick={() => abort.current?.abort()}>Stop</button>
              : <button type="submit" className="btn primary" disabled={!input.trim()}>Ask</button>}
          </form>
        </section>

        <aside className="stack" style={{ gap: 16 }}>
          <div className="card">
            <ScenarioSelect habitats={habitats.data} value={scenario} onChange={setScenario} label="Answer for habitat" />
            <p className="small muted" style={{ marginTop: 8 }}>The scenario's atmosphere and its top-ranked investigations are passed to the SI as context.</p>
          </div>
          <div className="card small">
            <h3>Engine</h3>
            {status.data?.engine === 'claude' ? (
              <p className="secondary">Claude ({status.data.model}) with the full PSI corpus in a prompt-cached context. Answers are generated and cite accession IDs.</p>
            ) : (
              <p className="secondary">Offline engine: BM25 retrieval, explainable ranking and rule-based gap analysis. Set <code>ANTHROPIC_API_KEY</code> in <code>.env</code> to enable Claude-generated answers.</p>
            )}
            {messages.length > 0 && <button className="btn sm ghost" onClick={() => setMessages([])} disabled={busy}>New conversation</button>}
          </div>
        </aside>
      </div>
    </>
  )
}
