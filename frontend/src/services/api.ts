import type { LibraryDataset } from './datasetLibrary'
import type { DatasetInspection, Experiment, ExperimentListItem, PredictionOutput, ResearchConfig, Row, TableResult, TransportMode } from '../types'

export class ApiError extends Error {
  constructor(message: string, public status: number) {super(message)}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  const headers = new Headers(init?.headers)
  try { response = await fetch('/api' + path, {...init, headers}) }
  catch { throw new Error("We can't connect to Transit Lab. Make sure the local server is running, then try again.") }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: 'The local server could not complete this request.' }))
    const message = Array.isArray(body.detail) ? body.detail.map((x: {msg: string}) => x.msg).join('; ') : body.detail
    throw new ApiError(message || `Request failed (${response.status})`, response.status)
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
  get: (id: string) => request<Experiment>(`/experiments/${id}`),
  cloudImport: (provider: 'google' | 'onedrive', url: string) => request<Experiment>('/cloud-import', json('POST', {provider, url})),
  library: () => request<LibraryDataset[]>('/datasets/library'),
  libraryFile: async (item: LibraryDataset): Promise<File> => {
    const content = await asset(`/api/datasets/library/${encodeURIComponent(item.id)}`)
    if (content.type.includes('text/html') || !content.size || content.size > 25 * 1024 * 1024) throw new Error('This library file could not be read. Try another dataset or upload a local file.')
    return new File([content], item.filename)
  },
  inspect: (file: File) => { const data = new FormData(); data.append('file', file); return request<DatasetInspection>('/datasets/inspect', {method: 'POST', body: data}) },
  upload: (file: File) => { const data = new FormData(); data.append('file', file); return request<Experiment>('/experiments', { method: 'POST', body: data }) },
  configure: (s: Experiment, config: ResearchConfig, approve = false) => request<Experiment>(`/experiments/${s.id}/config`, json('PUT', { revision: s.revision, config, approve_interactions: approve })),
  review: (s: Experiment, record_id: string, action: string, reason: string, corrections: Record<string, string | number>) => request<Experiment>(`/experiments/${s.id}/reviews`, json('PUT', { revision: s.revision, record_id, action, reason, corrections })),
  train: (s: Experiment, selection: string) => request(`/experiments/${s.id}/train`, json('POST', { revision: s.revision, selection })),
  analyze: (s: Experiment, approve: boolean, retain: boolean, reason: string) => request(`/experiments/${s.id}/analyze`, json('POST', {revision: s.revision, approve_interactions: approve, retain_remaining: retain, retain_reason: reason})),
  predict: (s: Experiment, file: File, mode: string, inputsAvailable: boolean) => {
    const data = new FormData()
    data.append('file', file)
    data.append('revision', String(s.revision))
    data.append('transport_mode', mode)
    data.append('inputs_available', String(inputsAvailable))
    return request<PredictionOutput>(`/experiments/${s.id}/predict`, {method: 'POST', body: data})
  },
  table: (id: string, name: string, search = '', offset = 0, limit = 25, transport_mode: TransportMode = 'all') => request<TableResult>(`/experiments/${id}/tables/${name}?${new URLSearchParams({search, transport_mode, offset: String(offset), limit: String(limit)})}`),
  record: (id: string, rid: string) => request<{ original: Row; decision: {action: string; reason: string; corrections: Row} | null; flagged: boolean }>(`/experiments/${id}/records/${encodeURIComponent(rid)}`),
}
export const downloadUrl = (s: Experiment, kind: string, table?: string) => `/api/experiments/${s.id}/download/${kind}${table ? '?table=' + encodeURIComponent(table) : ''}`
export const figureUrl = (s: Experiment, name: string, dark = false) => `/api/experiments/${s.id}/figures/${name}?revision=${s.revision}${dark ? '&theme=dark' : ''}`
