import { useEffect, useState } from 'react'
import { ArrowRight, Check, Clock3, Gauge, Table2, TrendingDown } from 'lucide-react'
import type { Experiment, Row, TransportMode } from '../types'
import { LABELS, TARGET } from '../types'
import { api } from '../services/api'
import { columnHelp, displayValue, performanceConclusion } from '../services/presentation'
import { Modal, format } from './Common'
import { DataTable } from './DataTable'
import { StationCondition } from './StationCondition'
import { TransportOutputs, TransportContext, observationMode } from './TransportOutputs'
import { ControlledComparisons, StatisticalChecks } from './ResearchProtocol'
import { ExportResults, ResearchDetails } from './ResearchDetails'
import { PredictionExplanations } from './PredictionExplanations'

const minutes = (value: unknown) => typeof value === 'number'
  ? value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '—'
const metricUnits = {MSE: 'squared minutes', RMSE: 'minutes', MAE: 'minutes', R2: 'share explained'} as const
const num = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
// Change from Traditional to Enhanced: percent for error metrics (lower is better), points for R² (higher is better).
function change(metric: keyof typeof metricUnits, before: unknown, after: unknown) {
  const a = num(before), b = num(after)
  if (a === null || b === null) return null
  if (metric === 'R2') { const d = b - a; return {text: `${d >= 0 ? '+' : '−'}${Math.abs(d).toFixed(3)}`, better: d > 0} }
  if (a === 0) return null
  const pct = (b - a) / a * 100
  return {text: `${pct > 0 ? '+' : '−'}${Math.abs(pct).toFixed(1)}%`, better: pct < 0}
}

export function AnalysisResults({s}: {s: Experiment}) {
  const [row, setRow] = useState<Row | null>(null)
  const [full, setFull] = useState(false)
  const [predictionOffset, setPredictionOffset] = useState(0)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<TransportMode>('all')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    setLoading(true); setRow(null); setError('')
    api.table(s.id, 'predictions', '', 0, 1, mode).then(data => {if (active) setRow(data.rows[0] || null)}).catch(e => {if (active) setError(e.message)}).finally(() => {if (active) setLoading(false)})
    return () => {active = false}
  }, [s.id, s.revision, mode])
  useEffect(() => {setPredictionOffset(0)}, [s.id, s.revision, mode])
  const traditional = s.metrics.find(m => m.Model === 'Baseline MLR')
  const enhanced = s.metrics.find(m => m.Model === 'Enhanced MLR')
  const condition = typeof row?.['Multi-Factor Station Score'] === 'number' ? String(row['Overall Station Classification']) : 'Requires Researcher Decision'
  const missing = String(row?.['Missing Classification Definitions'] || '').split(';').map(text => text.trim()).filter(Boolean).map(text =>
    / unit: /.test(text) ? `${text.split(' unit:')[0]}: the measurement unit needs to be defined.` : text
      .replace(': Insufficient Variation for Classification', ': the training data does not vary enough to support a condition.')
      .replace(': Requires Researcher Decision', ': a scoring rule is still unavailable.'))
  const baseErr = num(row?.['Baseline Error (actual - predicted)']), enhErr = num(row?.['Enhanced Error (actual - predicted)'])
  const closer = baseErr === null || enhErr === null || Math.abs(baseErr) === Math.abs(enhErr) ? null : Math.abs(enhErr) < Math.abs(baseErr) ? 'enhanced' : 'baseline'

  return <div className={`analysis-results output-mode-${observationMode(s, row)}`}>
    <TransportOutputs s={s} mode={mode} select={value => {if (value !== mode) {setMode(value); setRow(null); setLoading(true)}}}/>
    <div className="observation-toolbar">
      <div className="selected-observation"><span>Selected observation</span><strong>{row ? String(row['Record ID']) : loading ? 'Loading...' : '—'}</strong></div>
    </div>
    <div className="result-overview" key={`${mode}:${String(row?.['Record ID'] || 'loading')}`} aria-busy={loading}>
      {row && <TransportContext s={s} row={row}/>}
      <section className="prediction-section primary-prediction">
        <div className="result-label"><Clock3 size={18} aria-hidden="true"/><h3 title={columnHelp['Enhanced Predicted Waiting Time']}>Enhanced MLR Predicted Waiting Time</h3></div>
        {error ? <p role="alert" className="inline-error">{error}</p> : row ? <>
          <div className="primary-wait"><strong>{minutes(row['Enhanced Predicted Waiting Time'])}</strong><small>min</small></div>
          <p className="result-observation">Enhanced MLR estimate for this observation</p>
          {row['Enhanced Negative Prediction'] && <p className="result-note">Negative model estimate. See View Details.</p>}
        </> : loading ? <p role="status" className="muted">Loading prediction...</p> : <div className="transport-empty" role="status"><strong>No {mode === 'all' ? '' : mode === 'unspecified' ? 'unlabeled ' : `${mode} `}predictions in this test set</strong><p>Only labeled test observations appear in Bus and Train views. Use All to return to the complete results.</p></div>}
      </section>
      {row && <StationCondition s={s} row={row} summaryOnly/>}
      <section className="accuracy-summary">
        <div className="result-label"><Gauge size={18} aria-hidden="true"/><h3 title={columnHelp.RMSE}>Enhanced MLR RMSE</h3></div>
        <p><strong>{minutes(enhanced?.RMSE)}</strong> <span>min</span></p>
        <small className="accuracy-scope">Typical size of this model's prediction errors, in minutes. Larger errors count more heavily, so this is not a plain average.</small>
        <small className="accuracy-scope">Across all {s.test} test observations</small>
      </section>
    </div>
    <div className="result-actions">
    <button className="button predictions-trigger" disabled={!row} onClick={() => setFull(true)}><Table2 size={16}/>View Predictions<ArrowRight size={15}/></button>
    <ResearchDetails s={s} advanced={row && <StationCondition s={s} row={row}/>}>
      <section className="plain-summary">
        <h3>Summary</h3>
        {s.provenance && <details className="disclosure"><summary>Dataset source notes</summary><div className="disclosure-body"><p>{s.provenance.message}</p></div></details>}
        {row ? <><p>For observation <strong>{String(row['Record ID'])}</strong>, the Enhanced MLR predicted waiting time is <strong>{minutes(row['Enhanced Predicted Waiting Time'])} minutes</strong>.</p>
          {row['Enhanced Negative Prediction'] && <p className="decision-note">The model returned a negative estimate, so this is not a usable waiting-time forecast. The original value is retained so the evaluation remains transparent.</p>}
          <div className="details-tiles">
            <div><span>Enhanced MLR prediction</span><strong>{minutes(row['Enhanced Predicted Waiting Time'])}<small> min</small></strong></div>
            <div><span>Station condition</span><strong><span className={`condition-pill band-${LABELS.indexOf(condition)}`}>{condition}</span></strong></div>
            <div className="improvement"><span>RMSE, all test observations</span><strong>{minutes(traditional?.RMSE)} <ArrowRight size={15} aria-label="to"/> {minutes(enhanced?.RMSE)}<small> min</small></strong>
              {(() => {const c = change('RMSE', traditional?.RMSE, enhanced?.RMSE); return c && <em className={c.better ? 'better' : 'worse'}>{c.better && <TrendingDown size={14} aria-hidden="true"/>}{c.text}</em>})()}</div>
          </div>
          <p>{condition === 'Requires Researcher Decision' ? 'Some data or scoring rules need attention before a condition can be reported.' : 'The station condition combines the predicted wait with the six transportation factors for this observation.'}</p>
          {missing.length > 0 && <><ul className="summary-reasons">{missing.map(reason=><li key={reason}>{reason}</li>)}</ul><p className="section-caption">Rules and units can be reviewed in Model settings. Factors without enough variation need suitable recorded observations.</p></>}
        </> : <p className="muted">Select an observation once its prediction has loaded.</p>}
      </section>
      <section className="full-comparison">
        <h3>Model Performance</h3>
        <p className="section-caption">Traditional MLR is the baseline comparison. Both models were checked against the same {s.test} observations kept aside from training. Smaller error values mean closer predictions. This main comparison uses reviewed training data for both models (B vs C).</p>
        <div className="table-scroll"><table className="model-comparison" aria-label="Model comparison"><colgroup><col/><col/><col className="enhanced-col"/><col/></colgroup><thead><tr><th>Metric</th><th>Traditional MLR</th><th className="enhanced-head">Enhanced MLR</th><th>Change</th></tr></thead><tbody>{(['MSE', 'RMSE', 'MAE', 'R2'] as const).map(metric => <tr key={metric}><th scope="row" title={columnHelp[metric]}>{metric === 'R2' ? 'R²' : metric}<small>{metricUnits[metric]}</small></th><td>{format(traditional?.[metric], 4)}</td><td className="enhanced-cell">{format(enhanced?.[metric], 4)}</td><td className="change-cell">{(() => {const c = change(metric, traditional?.[metric], enhanced?.[metric]); return c ? <span className={c.better ? 'better' : 'worse'}>{c.better && <Check size={13} aria-hidden="true"/>}{c.text}</span> : '—'})()}</td></tr>)}</tbody></table></div>
        <p className="section-caption change-note">Change compares Enhanced with Traditional. For MSE, RMSE and MAE a negative change means smaller errors; for R² a positive change means more variation explained.</p>
        {!!s.mode_metrics?.length && <details className="disclosure"><summary>Performance by transport mode</summary><div className="disclosure-body"><p className="section-caption">These metrics describe this single-mode dataset. Bus and Train models are fitted separately.</p><div className="table-scroll"><table aria-label="Model performance by transport mode"><thead><tr><th>Transport mode</th><th>Model</th><th>Test rows</th><th>MSE</th><th>RMSE (min)</th><th>MAE (min)</th><th>R²</th></tr></thead><tbody>{s.mode_metrics.map((item, index) => <tr key={`${item['Transport Mode']}-${item.Model}-${index}`}><td>{format(item['Transport Mode'])}</td><td>{format(displayValue(item.Model))}</td><td>{format(item['Test Rows'], 0)}</td><td>{format(item.MSE, 4)}</td><td>{format(item.RMSE, 4)}</td><td>{format(item.MAE, 4)}</td><td>{format(item.R2, 4)}</td></tr>)}</tbody></table></div></div></details>}
        {s.station_aggregation && <details className="disclosure"><summary>Station-level summary</summary><div className="disclosure-body">
          <p className="section-caption">{s.station_aggregation.aggregation || s.station_aggregation.reason} {s.station_aggregation.available && `Grouped ${s.station_aggregation.station_count} stations; ${s.station_aggregation.ungrouped_records} test rows had no Station ID.`}</p>
          {s.station_aggregation.available && <DataTable s={s} name="station_summary"/>}
        </div></details>}
        <details className="disclosure"><summary>What do these metrics mean?</summary><dl className="metric-explanations disclosure-body"><div><dt>RMSE</dt><dd>{columnHelp.RMSE} It is measured in minutes, not a confidence percentage.</dd></div><div><dt>MSE</dt><dd>Averages squared prediction errors, giving larger mistakes more weight. Lower is better.</dd></div><div><dt>MAE</dt><dd>{columnHelp.MAE}</dd></div><div><dt>R²</dt><dd>{columnHelp.R2}</dd></div></dl></details>
        <p className="performance-conclusion">{performanceConclusion(s.conclusion)}</p>
        <ControlledComparisons s={s}/>
        <StatisticalChecks s={s}/>
      </section>
      <section className="prediction-details">
        <div className="result-section-heading"><h3>Prediction Details</h3></div>
        {row && <><p className="observation-label">Observation <strong>{String(row['Record ID'])}</strong>{s.metadata.map(k => row[k] != null ? <span key={k}>{k}: {String(row[k])}</span> : null)}</p>
          <dl className="prediction-reference"><div><dt title={columnHelp[TARGET]}>Actual Waiting Time</dt><dd>{minutes(row[TARGET])} <small>min</small></dd></div><div><dt title={columnHelp['Baseline Predicted Waiting Time']}>Traditional MLR Prediction</dt><dd>{minutes(row['Baseline Predicted Waiting Time'])} <small>min</small></dd></div><div><dt title={columnHelp['Enhanced Predicted Waiting Time']}>Enhanced MLR Prediction</dt><dd>{minutes(row['Enhanced Predicted Waiting Time'])} <small>min</small></dd></div></dl>
          <dl className="research-facts prediction-errors"><div><dt title={columnHelp['Prediction Error']}>Traditional Prediction Error</dt><dd>{closer === 'baseline' && <span className="closer-tag">Closer</span>}{format(row['Baseline Error (actual - predicted)'])} min</dd></div><div><dt title={columnHelp['Prediction Error']}>Enhanced Prediction Error</dt><dd>{closer === 'enhanced' && <span className="closer-tag">Closer</span>}{format(row['Enhanced Error (actual - predicted)'])} min</dd></div><div><dt title={columnHelp['Overall Station Classification']}>Station Condition</dt><dd><span className={`condition-pill band-${LABELS.indexOf(condition)}`}>{condition}</span></dd></div><div><dt title={columnHelp['Multi-Factor Station Score']}>Multi-Factor Score</dt><dd>{format(row['Multi-Factor Station Score'])}{typeof row['Multi-Factor Station Score'] === 'number' ? ' / 3' : ' (Requires Researcher Decision)'}</dd></div></dl>
          <details className="disclosure"><summary>What do these values mean?</summary><div className="disclosure-body"><PredictionExplanations/></div></details>
          {(row['Baseline Negative Prediction'] || row['Enhanced Negative Prediction']) && <p className="decision-note">Negative estimates stay unchanged in the error calculation. For station scoring only, a negative enhanced wait is treated as zero.</p>}
          {row['Unseen Categories'] && <p className="decision-note">Some categories were not present in the training data: {String(row['Unseen Categories'])}. Interpret this prediction with care.</p>}
        </>}
      </section>
    </ResearchDetails>
    <ExportResults s={s}/>
    </div>
    {full && <Modal title="Prediction results" close={() => setFull(false)} className="wide-modal predictions-modal"><div className="modal-body"><p className="muted">{mode === 'all' ? 'All test observations.' : `${mode === 'bus' ? 'Bus' : mode === 'train' ? 'Train' : 'Unspecified transport'} test observations.`} Select a row to update the main result.</p><p className="section-caption">Station Condition combines all six transportation factors and the Enhanced MLR predicted wait. The Multi-Factor Score is their average severity, from 0 to 3. See View Details for the threshold breakdown.</p><DataTable key={mode} variant="predictions" s={s} name="predictions" transportMode={mode} initialOffset={predictionOffset} onOffsetChange={setPredictionOffset} columns={['Record ID', TARGET, 'Baseline Predicted Waiting Time', 'Enhanced Predicted Waiting Time', 'Baseline Error (actual - predicted)', 'Enhanced Error (actual - predicted)', 'Overall Station Classification', 'Multi-Factor Station Score', ...s.metadata]} onRow={value => {setRow(value); setFull(false)}} actionLabel="Inspect"/><p className="section-caption">Waiting times and prediction errors are in minutes.</p><PredictionExplanations/></div></Modal>}
  </div>
}
