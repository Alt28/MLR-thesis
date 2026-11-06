import type { Experiment, ExperimentListItem, PredictionOutput, ResearchConfig, Row, TableResult, TransportMode } from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  const headers = new Headers(init?.headers)
  try { response = await fetch('/api' + path, {...init, headers}) }
  catch { throw new Error("We can't connect to Transit Lab. Make sure the local server is running, then try again.") }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'The local server could not complete this request.' }))
    const message = Array.isArray(body.detail) ? body.detail.map((x: {msg: string}) => x.msg).join('; ') : body.detail
    throw new Error(message || `Request failed (${response.status})`)
  }
  return response.json()
}
const json = (method: string, value: unknown) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) })
const asset = async (path: string): Promise<Blob> => {
  const response = await fetch(path)
  if (!response.ok) {
    const body = await response.json().catch(() => ({detail: 'The server could not provide this file.'}))
    throw new Error(body.detail || `Request failed (${response.status})`)
  }
  return response.blob()
}
export async function downloadFile(path: string, filename: string): Promise<void> {
  const blob = await asset(path)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export const api = {
  file: asset,
  list: () => request<ExperimentListItem[]>('/experiments'),
  cloudImport: (provider: 'google' | 'onedrive', url: string) => request<Experiment>('/cloud-import', json('POST', {provider, url})),
  libraryImport: async (filename: string): Promise<Experiment> => {
    let response: Response
    try {response = await fetch(`/assets/datasets/${encodeURIComponent(filename)}`)}
    catch {throw new Error("We couldn't load this dataset. Check that Transit Lab is running and try again.")}
    if (!response.ok) throw new Error('This library file is unavailable. Try again or upload a local dataset.')
    const content = await response.blob()
    if (content.type.includes('text/html') || !content.size || content.size > 25 * 1024 * 1024) throw new Error('This library file could not be read. Try another dataset or upload your own.')
    return api.upload(new File([content], filename, {type: content.type}))
  },
  get: (id: string) => request<Experiment>(`/experiments/${id}`),
  upload: (file: File) => { const data = new FormData(); data.append('file', file); return request<Experiment>('/experiments', { method: 'POST', body: data }) },
  configure: (s: Experiment, config: ResearchConfig, approve = false) => request<Experiment>(`/experiments/${s.id}/config`, json('PUT', { revision: s.revision, config, approve_interactions: approve })),
  review: (s: Experiment, record_id: string, action: string, reason: string, corrections: Record<string, string | number>) => request<Experiment>(`/experiments/${s.id}/reviews`, json('PUT', { revision: s.revision, record_id, action, reason, corrections })),
  train: (s: Experiment, selection: string) => request(`/experiments/${s.id}/train`, json('POST', { revision: s.revision, selection })),
  analyze: (s: Experiment, approve: boolean, retain: boolean, reason: string) => request(`/experiments/${s.id}/analyze`, json('POST', {revision: s.revision, approve_interactions: approve, retain_remaining: retain, retain_reason: reason})),
  predict: (s: Experiment, file: File) => {
    const data = new FormData()
    data.append('file', file)
    return request<PredictionOutput>(`/experiments/${s.id}/predict`, {method: 'POST', body: data})
  },
  table: (id: string, name: string, search = '', offset = 0, limit = 25, transport_mode: TransportMode = 'all') => request<TableResult>(`/experiments/${id}/tables/${name}?${new URLSearchParams({search, transport_mode, offset: String(offset), limit: String(limit)})}`),
  record: (id: string, rid: string) => request<{ original: Row; decision: {action: string; reason: string; corrections: Row} | null; flagged: boolean }>(`/experiments/${id}/records/${encodeURIComponent(rid)}`),
}
export const downloadUrl = (s: Experiment, kind: string, table?: string) => `/api/experiments/${s.id}/download/${kind}${table ? '?table=' + encodeURIComponent(table) : ''}`
export const figureUrl = (s: Experiment, name: string, dark = false) => `/api/experiments/${s.id}/figures/${name}?revision=${s.revision}${dark ? '&theme=dark' : ''}`
