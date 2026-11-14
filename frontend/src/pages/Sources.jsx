import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { ErrorBox, Loading, useAsync } from '../components/ui.jsx'

export default function Sources() {
  const [tick, setTick] = useState(0)
  const status = useAsync(() => api.ingestStatus(), [tick])
  const sources = useAsync(() => api.sources(), [])
  const ping = useAsync(() => api.psiPing(), [])
  const [msg, setMsg] = useState('')

  // poll while a sync is running
  useEffect(() => {
    if (!status.data?.syncing) return
    const t = setTimeout(() => setTick((n) => n + 1), 2500)
    return () => clearTimeout(t)
  }, [status.data])

  async function sync() {
    setMsg('')
    try { await api.sync('live'); setMsg('Live sync started.'); setTick((n) => n + 1) } catch (e) { setMsg(e.message) }
  }

  const s = status.data
  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Provenance</div>
          <h1>Data sources & live sync</h1>
          <p>
            Investigation metadata and test tables come from NASA's Physical Sciences Informatics (PSI) system through
            its public JSON web service. A bundled snapshot of the same data loads instantly on first start, and the
            ingestion service then refreshes from the live API.
          </p>
        </div>
      </div>

      <div className="grid g2" style={{ marginBottom: 16 }}>
        <section className="card">
          <div className="card-head">
            <h2>NASA PSI API</h2>
            <button className="btn primary" onClick={sync} disabled={s?.syncing}>{s?.syncing ? 'Syncing…' : '⟳ Sync now from NASA PSI'}</button>
          </div>
          {status.loading && !s ? <Loading /> : status.error ? <ErrorBox error={status.error} /> : (
            <>
              <dl className="kv">
                <dt>API reachable</dt><dd>{ping.loading ? 'checking…' : ping.data?.reachable ? '✓ yes' : '✗ no (snapshot in use)'}</dd>
                <dt>Endpoint</dt><dd className="mono small">{s.psi_api}</dd>
                <dt>Current data</dt><dd>{s.data_mode === 'live' ? 'Live PSI API' : 'Bundled snapshot'}{s.last_sync && ` · ${new Date(s.last_sync).toLocaleString()}`}</dd>
                <dt>Loaded</dt><dd>{s.investigations} investigations · {s.tables} tables · {s.test_rows} test rows</dd>
                {s.syncing && <><dt>Progress</dt><dd>{s.progress ? `${s.progress.done} / ${s.progress.total} investigations` : 'starting…'}</dd></>}
              </dl>
              {msg && <div className="notice" style={{ marginTop: 10 }}>{msg}</div>}
              <h3 style={{ marginTop: 16 }}>Sync history</h3>
              <div className="table-wrap" style={{ maxHeight: 260 }}>
                <table className="data">
                  <thead><tr><th>#</th><th>Mode</th><th>Status</th><th>Records</th><th>Finished</th><th>Message</th></tr></thead>
                  <tbody>{s.runs.map((r) => (
                    <tr key={r.id}><td className="num">{r.id}</td><td>{r.mode}</td><td>{r.status}</td><td className="num">{r.investigations}/{r.tables}</td>
                      <td className="small">{r.finished_at ? new Date(r.finished_at).toLocaleTimeString() : '—'}</td><td className="small secondary">{r.message}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            </>
          )}
        </section>

        <section className="card">
          <h2>How the data supports the solution</h2>
          <ul className="reasons" style={{ fontSize: 13.5 }}>
            <li><b>Summarize:</b> PSI objectives, hypotheses and approaches become SI briefs and searchable text.</li>
            <li><b>Extract:</b> each investigation's experimental-table CSV is parsed into O2, pressure, flow, fuels, and the parameters that varied or stayed constant.</li>
            <li><b>Rank:</b> the extracted conditions are scored against habitat atmospheres (ISS, Orion, Moon Base, rover, Mars, spacesuit).</li>
            <li><b>Interpret:</b> gap analysis shows where crewed atmospheres have no test data, and Claude answers questions grounded in the records.</li>
            <li><b>Model:</b> Data Lab exports clean CSV for calibrating and validating flammability and fire-spread models.</li>
          </ul>
          <div className="notice small" style={{ marginTop: 12 }}>
            Cite PSI data by DOI as NASA requests. Each investigation page links its DOI and PSI landing page.
          </div>
          <p className="small muted" style={{ marginTop: 10 }}>API docs: <a href="/api/catalog/docs" target="_blank" rel="noreferrer">catalog</a> · <a href="/api/insights/docs" target="_blank" rel="noreferrer">insights</a> · <a href="/api/ingest/docs" target="_blank" rel="noreferrer">ingestion</a></p>
        </section>
      </div>

      <section className="card">
        <h2>All sources</h2>
        {sources.loading ? <Loading /> : sources.error ? <ErrorBox error={sources.error} /> : (
          <div className="table-wrap" style={{ maxHeight: 'none' }}>
            <table className="data">
              <thead><tr><th>Source</th><th>Type</th><th>How it's used</th></tr></thead>
              <tbody>{sources.data.map((x) => (
                <tr key={x.url}><td><a href={x.url} target="_blank" rel="noreferrer">{x.name}</a></td><td className="small">{x.kind}</td><td className="small secondary">{x.use}</td></tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
