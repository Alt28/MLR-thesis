import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, LoaderCircle, Search } from 'lucide-react'
import { api } from '../services/api'
import type { Experiment, Row, TableResult, TransportMode } from '../types'
import { Empty, format, Badge } from './Common'
import { DragScroll } from './DragScroll'
import { columnHelp, columnLabel, displayValue } from '../services/presentation'

export function DataTable({s, name, onRow, actionLabel = 'Inspect', columns, emptyTitle = 'No records to display', transportMode = 'all', initialOffset = 0, onOffsetChange}: {s: Experiment; name: string; onRow?: (row: Row) => void; actionLabel?: string; columns?: string[]; emptyTitle?: string; transportMode?: TransportMode; initialOffset?: number; onOffsetChange?: (offset: number) => void}) {
  const [data, setData] = useState<TableResult | null>(null)
  const [query, setQuery] = useState('')
  const [offset, setOffsetState] = useState(initialOffset)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const scope = `${s.id}:${s.revision}:${name}:${transportMode}`
  const lastScope = useRef(scope)
  const setOffset = (value: number) => {setOffsetState(value); onOffsetChange?.(value)}
  useEffect(() => {
    if (lastScope.current === scope) return
    lastScope.current = scope
    setOffset(0); setQuery(''); setData(null); setLoading(true)
  }, [scope])
  useEffect(() => {
    let active = true
    const timer = setTimeout(() => {
      setLoading(true); setError('')
      api.table(s.id, name, query, offset, 25, transportMode).then(result => {if (active) setData(result)}).catch(e => {if (active) setError(e.message)}).finally(() => {if (active) setLoading(false)})
    }, query ? 220 : 0)
    return () => {active = false; clearTimeout(timer)}
  }, [s.id, s.revision, s.status, name, query, offset, transportMode])
  const visible = columns ? columns.filter(c => data?.columns.includes(c)) : data?.columns || []
  return <div className="data-table" aria-busy={loading}>
    <div className="table-toolbar"><label className="search"><Search size={16}/><input aria-label={`Search ${name}`} placeholder="Search observations…" value={query} onChange={e => {setQuery(e.target.value); setOffset(0)}}/></label><span className="muted">{loading ? 'Loading…' : `${format(data?.total, 0)} records`}</span></div>
    {loading && !data && <div className="table-loading" role="status"><LoaderCircle size={17} className="spinning"/>Loading observations…</div>}
    {error ? <div role="alert" className="inline-error">{error}</div> : data?.rows.length ? <DragScroll><table aria-label={name}><thead><tr>{visible.map(c => <th key={c} title={columnHelp[c]}>{columnLabel(c)}</th>)}{onRow && <th>Details</th>}</tr></thead><tbody>{data.rows.map((row, i) => <tr key={i}>{visible.map(c => <td key={c} className={typeof row[c] === 'number' ? 'numeric' : ''}>{c === 'Overall Station Classification' ? <Badge tone={String(row[c]).startsWith('Normal') ? 'success' : String(row[c]).startsWith('Severe') ? 'danger' : 'warning'}>{format(displayValue(row[c]))}</Badge> : format(displayValue(row[c]))}</td>)}{onRow && <td><button className="text-button" onClick={() => onRow(row)}>{actionLabel} <span aria-hidden>↗</span></button></td>}</tr>)}</tbody></table></DragScroll> : !loading && <Empty compact title={query ? 'No matching records' : emptyTitle} text={query ? 'Try another search term.' : 'Records will appear here when available for this experiment.'}/>}
    <div className="table-footer"><span>{data?.total ? `${offset + 1}–${Math.min(offset + 25, data.total)} of ${data.total}` : 'No rows'} · {onRow ? 'Open a record for details' : 'Scroll horizontally to view all columns'}</span><div><button className="icon-button" aria-label="Previous page" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 25))}><ChevronLeft size={17}/></button><button className="icon-button" aria-label="Next page" disabled={!data || offset + 25 >= data.total || loading} onClick={() => setOffset(offset + 25)}><ChevronRight size={17}/></button></div></div>
  </div>
}
