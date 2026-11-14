// Thin client for the three backend microservices behind the nginx gateway.
const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail || detail } catch { /* not JSON */ }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json()
}

export const api = {
  // catalog service
  investigations: (params = {}) => get(`/catalog/investigations?${new URLSearchParams(clean(params))}`),
  investigation: (acc) => get(`/catalog/investigations/${acc}`),
  tables: () => get('/catalog/tables'),
  table: (id) => get(`/catalog/tables/${id}`),
  tableCsvUrl: (id) => `${BASE}/catalog/tables/${id}/csv`,
  compare: (ids) => get(`/catalog/compare?ids=${ids.join(',')}`),
  stats: () => get('/catalog/stats'),
  conditions: () => get('/catalog/conditions'),
  habitats: () => get('/catalog/habitats'),
  incidents: () => get('/catalog/incidents'),
  spinoffs: () => get('/catalog/spinoffs'),
  facets: () => get('/catalog/facets'),
  // insights service
  insightsStatus: () => get('/insights/status'),
  rank: (scenario, focus = 'all') => get(`/insights/rank?scenario=${scenario}&focus=${focus}`),
  gaps: () => get('/insights/gaps'),
  recommendations: (scenario) => get(`/insights/recommendations?scenario=${scenario}`),
  search: (q) => get(`/insights/search?q=${encodeURIComponent(q)}`),
  brief: (acc, refresh = false) => get(`/insights/brief/${acc}${refresh ? '?refresh=true' : ''}`),
  // ingestion service
  ingestStatus: () => get('/ingest/status'),
  sources: () => get('/ingest/sources'),
  psiPing: () => get('/ingest/psi/ping'),
  sync: async (mode = 'live') => {
    const res = await fetch(`${BASE}/ingest/sync?mode=${mode}`, { method: 'POST' })
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText)
    return res.json()
  },
}

function clean(obj) {
  return Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== '' && v != null && v !== false))
}

/** Stream an SI answer via Server-Sent Events. onEvent receives {type, ...}. */
export async function askStream(body, onEvent, signal) {
  const res = await fetch(`${BASE}/insights/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`)
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    let idx
    while ((idx = buf.indexOf('\n\n')) >= 0) {
      const chunk = buf.slice(0, idx)
      buf = buf.slice(idx + 2)
      const line = chunk.split('\n').find((l) => l.startsWith('data: '))
      if (line) onEvent(JSON.parse(line.slice(6)))
    }
  }
}
