import { useState } from 'react'
import { Download, Upload } from 'lucide-react'
import type { Cell, Experiment, PredictionOutput, Row } from '../types'
import { api } from '../services/api'
import { columnHelp, columnLabel } from '../services/presentation'
import { format } from './Common'

function csvCell(value: Cell) {
  let text = value == null ? '' : String(value)
  if (typeof value === 'string' && /^[=+\-@\t\r]/.test(value)) text = "'" + value
  return `"${text.replaceAll('"', '""')}"`
}

function downloadCsv(result: PredictionOutput) {
  const content = [result.columns, ...result.rows.map(row => result.columns.map(column => row[column]))]
    .map(row => row.map(csvCell).join(',')).join('\r\n')
  const url = URL.createObjectURL(new Blob(['\uFEFF', content], {type: 'text/csv;charset=utf-8'}))
  const link = document.createElement('a')
  link.href = url
  link.download = 'prediction_results.csv'
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function PredictionOnly({s}: {s: Experiment}) {
  const [result, setResult] = useState<PredictionOutput | null>(null)
  const [error, setError] = useState('')
  const [working, setWorking] = useState(false)

  const predict = async (file?: File) => {
    if (!file) return
    setWorking(true); setError(''); setResult(null)
    try { setResult(await api.predict(s, file)) }
    catch (e) { setError(e instanceof Error ? e.message : 'Prediction failed.') }
    finally { setWorking(false) }
  }

  const previewColumns = ['Record ID', 'Enhanced Predicted Waiting Time', 'Baseline Predicted Waiting Time',
    'Overall Station Classification', 'Multi-Factor Station Score'].filter(column => result?.columns.includes(column))

  return <section className="prediction-only">
    <h3>Predict new observations</h3>
    <p className="section-caption">Upload CSV/XLSX rows with all six predictors and no Actual Waiting Time. These forecasts are separate from the held-out evaluation and do not change the trained models or reported metrics. Actual waiting times and prediction errors are unavailable for these new observations.</p>
    <label className="button small prediction-upload">
      <Upload size={15}/>{working ? 'Predicting…' : 'Choose prediction dataset'}
      <input type="file" accept=".csv,.xlsx" disabled={working} onChange={event => {
        void predict(event.target.files?.[0])
        event.target.value = ''
      }}/>
    </label>
    {error && <p className="inline-error" role="alert">{error}</p>}
    {result && <>
      <p className="section-caption">{result.rows.length} predictions generated with model revision {result.model_revision}.</p>
      {result.station_aggregation.available
        ? <p className="section-caption">{result.station_aggregation.station_count} station summaries; {result.station_aggregation.ungrouped_records} records without a Station ID.</p>
        : <p className="section-caption">{result.station_aggregation.reason}</p>}
      <div className="table-scroll"><table aria-label="Prediction-only results">
        <thead><tr>{previewColumns.map(column => <th key={column} title={columnHelp[column]}>{columnLabel(column)}</th>)}</tr></thead>
        <tbody>{result.rows.slice(0, 10).map((row, index) => <tr key={String(row['Record ID'] ?? index)}>
          {previewColumns.map(column => <td key={column}>{format(row[column])}</td>)}
        </tr>)}</tbody>
      </table></div>
      {result.station_summary.length > 0 && <div className="table-scroll prediction-station-summary">
        <h4>Station summaries</h4>
        <table aria-label="Prediction-only station summaries">
          <thead><tr>{Object.keys(result.station_summary[0]).map(column => <th key={column}>{column}</th>)}</tr></thead>
          <tbody>{result.station_summary.slice(0, 10).map((row: Row, index) => <tr key={index}>
            {Object.keys(result.station_summary[0]).map(column => <td key={column}>{format(row[column])}</td>)}
          </tr>)}</tbody>
        </table>
      </div>}
      <button className="button small" onClick={() => downloadCsv(result)}><Download size={15}/>Download all prediction results</button>
    </>}
  </section>
}
