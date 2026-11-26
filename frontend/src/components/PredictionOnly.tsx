import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Download, Search } from 'lucide-react'
import type { Cell, DatasetInspection, Experiment, PredictionOutput, Row } from '../types'
import { columnHelp, displayValue } from '../services/presentation'
import { format } from './Common'
import { ExplainDrawer } from './ExplainDrawer'
import { Condition, station, when } from './PredictionTable'

export interface PredictionDataset {file: File; inspection: DatasetInspection}

function csvCell(value: Cell) {
  let text = value == null ? '' : String(value)
  if (typeof value === 'string' && /^[=+\-@\t\r]/.test(value)) text = "'" + value
  return `"${text.replaceAll('"', '""')}"`
}

function downloadCsv(result: PredictionOutput) {
  const columns = ['Actual Waiting Time', ...result.columns]
  const content = [columns, ...result.rows.map(row => columns.map(column => row[column]))]
    .map(row => row.map(csvCell).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF', content], {type: 'text/csv;charset=utf-8'}))
  const link = document.createElement('a')
  link.href = url
  link.download = 'prediction_results.csv'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

const PAGE = 15
const CONDITIONS = ['All', 'Normal Operation', 'Minor Delay', 'Moderate Delay', 'Severe Delay']
const SEARCHABLE = ['Record ID', 'Station / Stop', 'Time of Day', 'Day of Week', 'Month of Year', 'Observation Hour Local', 'Overall Station Classification']
const minutes = (value: Cell) => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—'

export function PredictionResults({s, result}: {s: Experiment; result: PredictionOutput}) {
  const [selected, setSelected] = useState(-1)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [condition, setCondition] = useState('All')
  const [page, setPage] = useState(0)

  const indexed = useMemo(() => result.rows.map((row, index) => ({row, index,
    text: SEARCHABLE.map(c => row[c] == null ? '' : String(row[c])).join(' ').toLowerCase()})), [result])
  const counts = useMemo(() => {
    const c: Record<string, number> = {All: result.rows.length}
    for (const row of result.rows) { const k = String(row['Overall Station Classification'] ?? ''); c[k] = (c[k] || 0) + 1 }
    return c
  }, [result])
  const filtered = useMemo(() => {
    const terms = query.toLowerCase().split(/\s+/).filter(Boolean)
    return indexed.filter(item => (condition === 'All' || item.row['Overall Station Classification'] === condition)
      && terms.every(t => item.text.includes(t)))
  }, [indexed, query, condition])
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE))
  const current = Math.min(page, pages - 1)
  const visible = filtered.slice(current * PAGE, current * PAGE + PAGE)
  const explain = (index: number) => {setSelected(index); setOpen(true)}
  const position = filtered.findIndex(item => item.index === selected)
  const move = (p: number) => {const next = filtered[p]; if (next) {setSelected(next.index); setPage(Math.floor(p / PAGE))}}

  return <section className="uploaded-predictions" aria-label="Predictions for uploaded dataset">
    <h3>Traditional vs Enhanced MLR</h3>
    <p className="section-caption">Traditional MLR and Enhanced MLR are each model's predicted waiting time, in minutes. Search or filter to find a specific observation, then choose <strong>Explain</strong> to open a panel showing how its station condition was scored.</p>
      <p className="forecast-result-count" role="status">{result.rows.length.toLocaleString()} predictions generated with model revision {result.model_revision}.</p>
      <div className="forecast-toolbar">
        <label className="search"><Search size={16}/><input aria-label="Search predictions" placeholder="Search station, day, month, time or ID…" value={query} onChange={e => {setQuery(e.target.value); setPage(0)}}/></label>
        <div className="forecast-filters" role="group" aria-label="Filter by station condition">{CONDITIONS.filter(c => c === 'All' || counts[c]).map(c =>
          <button key={c} type="button" className={`forecast-chip${condition === c ? ' active' : ''}`} aria-pressed={condition === c} onClick={() => {setCondition(c); setPage(0)}}>
            {c === 'All' ? 'All' : c.replace(' Operation', '')}<span>{(counts[c] || 0).toLocaleString()}</span></button>)}</div>
      </div>
      <div className="table-scroll" tabIndex={0} aria-label="Scroll forecast comparison"><table aria-label="Prediction-only results" className="prediction-table forecast-table">
        <colgroup><col style={{width: '36%'}}/><col style={{width: '14%'}}/><col style={{width: '14%'}}/><col style={{width: '24%'}}/><col style={{width: '12%'}}/></colgroup>
        <thead><tr><th>Observation</th><th className="num" title={columnHelp['Baseline Predicted Waiting Time']}>Traditional (min)</th><th className="num" title={columnHelp['Enhanced Predicted Waiting Time']}>Enhanced (min)</th><th>Station condition</th><th><span className="visually-hidden">Explain</span></th></tr></thead>
        <tbody>{visible.map(({row, index}) => { const id = String(row['Record ID'] ?? ''); return <tr key={id || index} className={index === selected ? 'selected' : ''}>
          <td><div className="pt-obs"><code title={id}>{id.length > 18 ? `${id.slice(0, 16)}…` : id}</code><strong>{station(row)}</strong><small>{when(row)}</small></div></td>
          <td className="num pt-trad" data-label="Traditional"><div className="pt-prediction"><strong>{minutes(row['Baseline Predicted Waiting Time'])}</strong></div></td>
          <td className="num pt-enh" data-label="Enhanced"><div className="pt-prediction"><strong>{minutes(row['Enhanced Predicted Waiting Time'])}</strong></div></td>
          <td className="pt-cond"><Condition label={row['Overall Station Classification']} score={row['Multi-Factor Station Score']}/></td>
          <td className="pt-action"><button type="button" className="text-button" aria-label={`Explain ${id}`} onClick={() => explain(index)}>Explain <span aria-hidden>↗</span></button></td>
        </tr>})}</tbody>
      </table></div>
      {!filtered.length && <p className="section-caption">No predictions match this search.</p>}
      <div className="table-footer"><span>{filtered.length ? `${(current * PAGE + 1).toLocaleString()}–${Math.min(filtered.length, current * PAGE + PAGE).toLocaleString()} of ${filtered.length.toLocaleString()}` : 'No rows'}{filtered.length !== result.rows.length ? ` (filtered from ${result.rows.length.toLocaleString()})` : ''}</span>
        <div><button className="icon-button" aria-label="Previous predictions page" disabled={current === 0} onClick={() => setPage(current - 1)}><ChevronLeft size={17}/></button><span className="forecast-page">Page {current + 1} of {pages.toLocaleString()}</span><button className="icon-button" aria-label="Next predictions page" disabled={current >= pages - 1} onClick={() => setPage(current + 1)}><ChevronRight size={17}/></button></div></div>
      <p className="section-caption">{result.station_aggregation.available ? `${result.station_aggregation.station_count} station summaries; ${result.station_aggregation.ungrouped_records} records without a station identifier.` : result.station_aggregation.reason}</p>
      {result.station_summary.length > 0 && <details className="disclosure prediction-station-summary"><summary>Station summaries</summary><div className="disclosure-body table-scroll">
        <table aria-label="Prediction-only station summaries">
          <thead><tr>{Object.keys(result.station_summary[0]).map(column => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>{result.station_summary.slice(0, 10).map((row: Row, index) => <tr key={index}>
            {Object.keys(result.station_summary[0]).map(column => <td key={column}>{format(displayValue(row[column]))}</td>)}
          </tr>)}</tbody>
        </table>
        {result.station_summary.length > 10 && <p>First 10 stations. The downloaded observation results include every station's records.</p>}
      </div></details>}
      <button className="button small" onClick={() => downloadCsv(result)}><Download size={15}/>Download all prediction results</button>
      {open && position >= 0 && <ExplainDrawer s={s} rows={filtered.map(item => item.row)} position={position} onMove={move} close={() => setOpen(false)}/>}
  </section>
}
