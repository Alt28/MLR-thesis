import { useState } from 'react'
import { Download } from 'lucide-react'
import type { Cell, DatasetInspection, Experiment, PredictionOutput, Row } from '../types'
import { columnHelp, columnLabel, displayValue } from '../services/presentation'
import { format } from './Common'
import { StationCondition } from './StationCondition'

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

export function PredictionResults({s, result}: {s: Experiment; result: PredictionOutput}) {
  const [selected, setSelected] = useState(0)

  const previewColumns = ['Record ID', 'Baseline Predicted Waiting Time', 'Enhanced Predicted Waiting Time',
    'Overall Station Classification', 'Multi-Factor Station Score'].filter(column => result?.columns.includes(column))

  return <section className="uploaded-predictions" aria-label="Predictions for uploaded dataset">
    <h3>Traditional vs Enhanced MLR</h3>
    <p className="section-caption">Both predictions are in minutes. Actual Waiting Time stays blank because it has not been measured. MSE, RMSE, and prediction errors are unavailable for these rows.</p>
      <p className="forecast-result-count" role="status">{result.rows.length} predictions generated with model revision {result.model_revision}.</p>
      <p className="section-caption">Preview: first {Math.min(10, result.rows.length)} rows. Download the complete results below. Predictions do not change the trained models or their evaluation results.</p>
      <div className="table-scroll" tabIndex={0} aria-label="Scroll forecast comparison"><table aria-label="Prediction-only results">
        <thead><tr><th>Actual Waiting Time</th>{previewColumns.map(column => <th key={column} title={columnHelp[column]}>{columnLabel(column)}</th>)}</tr></thead>
        <tbody>{result.rows.slice(0, 10).map((row, index) => <tr key={String(row['Record ID'] ?? index)}>
          <td>Not recorded</td>{previewColumns.map(column => <td key={column}>{format(displayValue(row[column]))}</td>)}
        </tr>)}</tbody>
      </table></div>
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
      <details className="disclosure forecast-scoring"><summary>SOP 3: show station scoring for a prediction</summary><div className="disclosure-body">
        <label>Prediction observation<select aria-label="Prediction observation" value={selected} onChange={e => setSelected(Number(e.target.value))}>{result.rows.map((row, index) => <option key={index} value={index}>{String(row['Record ID'])}</option>)}</select></label>
        <StationCondition s={s} row={result.rows[selected]} expanded/>
      </div></details>
  </section>
}
