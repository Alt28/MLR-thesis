import { useEffect, useState } from 'react'
import { ArrowRight, Clock3, Gauge, Table2 } from 'lucide-react'
import type { Experiment, Row, TransportMode } from '../types'
import { TARGET } from '../types'
import { api } from '../services/api'
import { Modal, format } from './Common'
import { DataTable } from './DataTable'
import { StationCondition } from './StationCondition'
import { TransportOutputs, TransportContext, observationMode } from './TransportOutputs'
import { ControlledComparisons } from './ResearchProtocol'
import { ExportResults, ResearchDetails } from './ResearchDetails'
import { PredictionOnly } from './PredictionOnly'

const minutes = (value: unknown) => typeof value === 'number'
  ? value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '—'

export function AnalysisResults({s}: {s: Experiment}) {
  const [row, setRow] = useState<Row | null>(null)
  const [full, setFull] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<TransportMode>('all')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    setLoading(true); setRow(null); setError('')
    api.table(s.id, 'predictions', '', 0, 1, mode).then(data => {if (active) setRow(data.rows[0] || null)}).catch(e => {if (active) setError(e.message)}).finally(() => {if (active) setLoading(false)})
    return () => {active = false}
  }, [s.id, s.revision, mode])
  const traditional = s.metrics.find(m => m.Model === 'Baseline MLR')
  const enhanced = s.metrics.find(m => m.Model === 'Enhanced MLR')
  const condition = typeof row?.['Multi-Factor Station Score'] === 'number' ? String(row['Overall Station Classification']) : 'Requires Researcher Decision'
  const missing = String(row?.['Missing Classification Definitions'] || '').split(';').map(text => text.trim()).filter(Boolean).map(text =>
    text.includes('Vehicle Frequency unit') ? 'Vehicle Frequency: the measurement unit needs to be defined.' : text
      .replace(': Insufficient Variation for Classification', ': the training data does not vary enough to support a condition.')
      .replace(': Requires Researcher Decision', ': a scoring rule is still unavailable.'))

  return <div className={`analysis-results output-mode-${observationMode(s, row)}`}>
    <TransportOutputs s={s} mode={mode} select={value => {if (value !== mode) {setMode(value); setRow(null); setLoading(true)}}}/>
    <div className="observation-toolbar">
      <div className="selected-observation"><span>Selected observation</span><strong>{row ? String(row['Record ID']) : loading ? 'Loading...' : '—'}</strong></div>
    </div>
    <div className="result-overview" key={`${mode}:${String(row?.['Record ID'] || 'loading')}`} aria-busy={loading}>
      {row && <TransportContext s={s} row={row}/>}
      <section className="prediction-section primary-prediction">
        <div className="result-label"><Clock3 size={18} aria-hidden="true"/><h3>Predicted Waiting Time</h3></div>
        {error ? <p role="alert" className="inline-error">{error}</p> : row ? <>
          <div className="primary-wait"><strong>{minutes(row['Enhanced Predicted Waiting Time'])}</strong><small>min</small></div>
          <p className="result-observation">Estimated wait for this observation</p>
          {row['Enhanced Negative Prediction'] && <p className="result-note">Negative model estimate. See View Details.</p>}
        </> : loading ? <p role="status" className="muted">Loading prediction...</p> : <div className="transport-empty" role="status"><strong>No {mode === 'all' ? '' : mode === 'unspecified' ? 'unlabeled ' : `${mode} `}predictions in this test set</strong><p>Only labeled test observations appear in Bus and Train views. Use All to return to the complete results.</p></div>}
      </section>
      {row && <StationCondition s={s} row={row} summaryOnly/>}
      <section className="accuracy-summary">
        <div className="result-label"><Gauge size={18} aria-hidden="true"/><h3>Model Accuracy</h3></div>
        <p>Enhanced MLR RMSE: <strong>{minutes(enhanced?.RMSE)}</strong> <span>min</span></p><small className="accuracy-scope">Across all {s.test} test observations</small>
      </section>
    </div>
    <div className="result-actions">
    <button className="button predictions-trigger" disabled={!row} onClick={() => setFull(true)}><Table2 size={16}/>View Predictions<ArrowRight size={15}/></button>
    <ResearchDetails s={s} advanced={row && <StationCondition s={s} row={row}/>}>
      <section className="plain-summary">
        <h3>Summary</h3>
        {s.provenance && <p className="decision-note">{s.provenance.message}</p>}
        {row ? <><p>For observation <strong>{String(row['Record ID'])}</strong>, the predicted waiting time is <strong>{minutes(row['Enhanced Predicted Waiting Time'])} minutes</strong>.</p>
          {row['Enhanced Negative Prediction'] && <p className="decision-note">The model returned a negative estimate, so this is not a usable waiting-time forecast. The original value is retained so the evaluation remains transparent.</p>}
          <p>Station condition: <strong>{condition}</strong>. {condition === 'Requires Researcher Decision' ? 'Some data or scoring rules need attention before a condition can be reported.' : 'This combines the predicted wait with the six transportation factors for this observation.'}</p>
          {missing.length > 0 && <><ul className="summary-reasons">{missing.map(reason=><li key={reason}>{reason}</li>)}</ul><p className="section-caption">Rules and units can be reviewed in Advanced Settings. Factors without enough variation need suitable recorded observations.</p></>}
        </> : <p className="muted">Select an observation once its prediction has loaded.</p>}
      </section>
      <section className="full-comparison">
        <h3>Model Performance</h3>
        <p className="section-caption">Both models were checked against the same {s.test} observations kept aside from training. Smaller error values mean closer predictions. This main comparison uses reviewed training data for both models (B vs C).</p>
        <div className="table-scroll"><table className="model-comparison" aria-label="Model comparison"><thead><tr><th>Metric</th><th>Traditional MLR</th><th>Enhanced MLR</th></tr></thead><tbody>{(['MSE', 'RMSE'] as const).map(metric => <tr key={metric}><th scope="row">{metric}<small>{metric === 'MSE' ? 'squared minutes' : 'minutes'}</small></th><td>{format(traditional?.[metric], 4)}</td><td>{format(enhanced?.[metric], 4)}</td></tr>)}</tbody></table></div>
        {!!s.mode_metrics?.length && <><h4>Performance by transport mode</h4><p className="section-caption">Separate test-set metrics are shown only for modes present in the test data. These are subsets of the pooled evaluation.</p><div className="table-scroll"><table aria-label="Model performance by transport mode"><thead><tr><th>Transport mode</th><th>Model</th><th>Test rows</th><th>MSE</th><th>RMSE (min)</th></tr></thead><tbody>{s.mode_metrics.map((item, index) => <tr key={`${item['Transport Mode']}-${item.Model}-${index}`}><td>{format(item['Transport Mode'])}</td><td>{format(item.Model)}</td><td>{format(item['Test Rows'], 0)}</td><td>{format(item.MSE, 4)}</td><td>{format(item.RMSE, 4)}</td></tr>)}</tbody></table></div></>}
        {s.station_aggregation && <details className="disclosure"><summary>Station-level summary</summary><div className="disclosure-body">
          <p className="section-caption">{s.station_aggregation.aggregation || s.station_aggregation.reason} {s.station_aggregation.available && `Grouped ${s.station_aggregation.station_count} stations; ${s.station_aggregation.ungrouped_records} test rows had no Station ID.`}</p>
          {s.station_aggregation.available && <DataTable s={s} name="station_summary"/>}
        </div></details>}
        <dl className="metric-explanations"><div><dt>RMSE</dt><dd>Summarizes how far predictions are from actual waits, in minutes. Lower is better; it is not a confidence percentage.</dd></div><div><dt>MSE</dt><dd>Averages squared prediction errors, giving larger mistakes more weight. Lower is better.</dd></div></dl>
        <p className="performance-conclusion">{s.conclusion?.replaceAll('Baseline', 'Traditional').replaceAll('baseline', 'traditional').replace('held-out', 'evaluation')}</p>
        <ControlledComparisons s={s}/>
      </section>
      <PredictionOnly s={s}/>
      <section className="prediction-details">
        <div className="result-section-heading"><h3>Prediction Details</h3></div>
        {row && <><p className="observation-label">Observation <strong>{String(row['Record ID'])}</strong>{s.metadata.map(k => row[k] != null ? <span key={k}>{k}: {String(row[k])}</span> : null)}</p>
          <dl className="prediction-reference"><div><dt>Actual wait</dt><dd>{minutes(row[TARGET])} <small>min</small></dd></div><div><dt>Traditional prediction</dt><dd>{minutes(row['Baseline Predicted Waiting Time'])} <small>min</small></dd></div><div><dt>Enhanced prediction</dt><dd>{minutes(row['Enhanced Predicted Waiting Time'])} <small>min</small></dd></div></dl>
          <dl className="research-facts prediction-errors"><div><dt>Traditional prediction error</dt><dd>{format(row['Baseline Error (actual - predicted)'])} min</dd></div><div><dt>Enhanced prediction error</dt><dd>{format(row['Enhanced Error (actual - predicted)'])} min</dd></div></dl>
          <p className="section-caption">Positive error means the prediction was too low; negative error means it was too high. Values near zero mean a closer estimate.</p>
          {(row['Baseline Negative Prediction'] || row['Enhanced Negative Prediction']) && <p className="decision-note">Negative estimates stay unchanged in the error calculation. For station scoring only, a negative enhanced wait is treated as zero.</p>}
          {row['Unseen Categories'] && <p className="decision-note">Some categories were not present in the training data: {String(row['Unseen Categories'])}. Interpret this prediction with care.</p>}
        </>}
      </section>
    </ResearchDetails>
    <ExportResults s={s}/>
    </div>
    {full && <Modal title="Prediction results" close={() => setFull(false)} className="wide-modal"><div className="modal-body"><p className="muted">{mode === 'all' ? 'All test observations.' : `${mode === 'bus' ? 'Bus' : mode === 'train' ? 'Train' : 'Unspecified transport'} test observations.`} Select a row to update the main result.</p><p className="section-caption">Station Condition combines all six transportation factors and the enhanced predicted wait. The Multi-Factor Score is their average severity, from 0 to 3. See View Details for the threshold breakdown.</p><DataTable key={mode} s={s} name="predictions" transportMode={mode} columns={['Record ID', 'Enhanced Predicted Waiting Time', 'Overall Station Classification', 'Multi-Factor Station Score', ...s.metadata, TARGET, 'Baseline Predicted Waiting Time', 'Baseline Error (actual - predicted)', 'Enhanced Error (actual - predicted)']} onRow={value => {setRow(value); setFull(false)}} actionLabel="Inspect observation"/></div></Modal>}
  </div>
}
