import { useState } from 'react'
import type { Experiment, ResearchConfig } from '../types'
import type { Workspace } from '../hooks/useExperiment'
import { Modal, format } from './Common'

const fields = [
  ['source_reference', 'Dataset source / reference', 'Name the provider, file, URL, or collection record.'],
  ['observation_definition', 'What does one row represent?', 'Specify station/route, mode, observation interval, and how predictors match the measured wait.'],
  ['collection_period', 'Collection period', 'Record dates and coverage; identify train and bus coverage separately.'],
  ['split_rationale', 'Evaluation split rationale', 'The current split is random. Explain independence of rows; repeated stations/trips or time-dependent records may require a different approved design.'],
  ['interaction_rationale', 'Interaction-term rationale', 'Explain why the selected combinations are justified before inspecting test results.'],
  ['classification_rationale', 'Classification-rule rationale', 'Document score weights, thresholds, directions, units, and evidence or approval for their use.'],
]

export function ResearchDocumentation({s, w, close}: {s: Experiment; w: Workspace; close: () => void}) {
  const [notes, setNotes] = useState<NonNullable<ResearchConfig['research_notes']>>({...s.config.research_notes})
  const [targets, setTargets] = useState(s.config.observed_targets_confirmed)
  const [available, setAvailable] = useState(s.config.prediction_inputs_available)
  return <Modal title="Research documentation" close={close} canClose={!w.busy} className="wide-modal"><form onSubmit={e => {
    e.preventDefault()
    void w.configure({...s.config, observed_targets_confirmed:targets, prediction_inputs_available:available, research_notes: Object.fromEntries(Object.entries(notes).map(([key, value]) => [key, value.trim()]))}).then(close).catch(() => {})
  }}><div className="modal-body">
    <p className="muted">These notes are researcher declarations, not automatic verification. Saving records a new revision; analyze again to include them in the exported results.</p>
    {s.provenance?.workbook_declares_prototype && <p className="decision-note">The workbook declares prototype or simulated data. A recorded-data selection cannot override that declaration.</p>}
    <label>Data source type<select aria-label="Data source type" value={notes.source_type || 'unknown'} disabled={w.busy} onChange={e => setNotes({...notes, source_type: e.target.value})}><option value="unknown">Not documented yet</option><option value="recorded">Recorded observations (researcher declaration)</option><option value="simulated">Simulated / prototype data</option></select></label>
    <label>Dataset transport mode<select aria-label="Dataset transport mode" disabled={w.busy} value={notes.transport_mode || 'unknown'} onChange={e => setNotes({...notes, transport_mode: e.target.value})}><option value="unknown">Not specified</option><option value="bus">Bus only</option><option value="train">Train only</option></select><small>Use one mode per dataset and train separate Bus and Train models. Recorded row labels must match this declaration.</small></label>
    <label className="checkbox-line"><input type="checkbox" aria-label="Confirm recorded waiting times" checked={targets} onChange={e=>setTargets(e.target.checked)}/>Actual Waiting Time contains genuine recorded passenger waits, not estimates from frequency or simulated values.</label>
    <label className="checkbox-line"><input type="checkbox" aria-label="Confirm training input availability" checked={available} onChange={e=>setAvailable(e.target.checked)}/>Passenger Volume and Vehicle Frequency use completed observation windows available at the intended prediction time.</label>
    <p className="section-caption">NYC station-complex counts may span platforms. AC Transit APC may cover only equipped buses. SUNT presence counts need distinct arrival identification before they represent hourly service frequency. Document these limits in the row definition below.</p>
    {fields.map(([key, label, hint]) => <label key={key}>{label}<textarea aria-label={label} aria-describedby={`research-note-${key}`} rows={2} maxLength={4000} disabled={w.busy} value={notes[key] || ''} onChange={e => setNotes({...notes, [key]: e.target.value})}/><small id={`research-note-${key}`}>{hint}</small></label>)}
    {!!s.provenance?.workbook_notes.length && <details className="disclosure"><summary>Source notes supplied with the workbook</summary><div className="disclosure-body">{s.provenance.workbook_notes.map((row, index) => <p className="section-caption" key={index}>{Object.values(row).join(' | ')}</p>)}</div></details>}
    {w.error && <p className="inline-error" role="alert">{w.error}</p>}
  </div><div className="modal-footer"><button type="button" className="button" disabled={w.busy} onClick={close}>Cancel</button><button className="button primary" disabled={w.busy}>Save research notes</button></div></form></Modal>
}

export function ControlledComparisons({s}: {s: Experiment}) {
  return <details className="disclosure controlled-comparisons"><summary>Separate data review and interaction effects</summary><div className="disclosure-body">
    {!s.study_available ? <p className="decision-note">This saved run predates the three-arm protocol. Select Train & evaluate again to generate the additional comparison.</p> : <>
      <p className="section-caption">All three experiments use the same {s.test} test observations. A uses the original training records. B uses reviewed records. C adds selected interactions to the same reviewed records as B.</p>
      <div className="table-scroll"><table aria-label="Controlled experiment metrics"><thead><tr><th>Experiment</th><th>Training rows</th><th>MSE</th><th>RMSE (min)</th></tr></thead><tbody>{s.study_metrics?.map(row => <tr key={String(row.Arm)}><th scope="row">{String(row.Arm)}: {String(row.Model)}</th><td>{format(row['Training Rows'], 0)}</td><td>{format(row.MSE, 4)}</td><td>{format(row.RMSE, 4)}</td></tr>)}</tbody></table></div>
      <ul className="protocol-comparisons">{s.study_comparisons?.map(row => <li key={String(row.Comparison)}><strong>{String(row.Comparison)}: {String(row.Question)}</strong><span>{String(row['Outcome for second arm'])}. RMSE reduction: {format(row['RMSE reduction (min)'], 4)} min.</span></li>)}</ul>
      <p className="section-caption">Positive reductions mean lower error for the second experiment; negative values mean higher error. Flagging records alone does not demonstrate an IQR benefit. See Statistical checks for paired tests and cross-validation.</p>
    </>}
  </div></details>
}

const pValue = (value: unknown) => typeof value !== 'number' ? '—' : value < 0.001 ? '< 0.001' : value.toFixed(3)

export function StatisticalChecks({s}: {s: Experiment}) {
  const v = s.validation
  const mseRow = v?.cv_summary.find(row => row.Metric === 'MSE')
  const cvTest = v?.cv_test[0]
  const agreement = Object.fromEntries((v?.classification ?? []).map(row => [String(row.Measure), row.Value]))
  return <details className="disclosure statistical-checks"><summary>Statistical checks</summary><div className="disclosure-body">
    {!v?.available ? <p className="decision-note">This saved run predates the statistical checks. Select Train & evaluate again to generate them.</p> : <>
      <h4>Paired tests on the {s.test} evaluation observations</h4>
      <p className="section-caption">Each observation's squared error under the first experiment minus the second. p-values below 0.05 indicate a difference unlikely under no true difference, for this dataset only.</p>
      <div className="table-scroll"><table aria-label="Paired significance tests"><thead><tr><th>Comparison</th><th>Test</th><th>p-value</th><th>Result</th></tr></thead><tbody>{v.heldout.map((row, index) => <tr key={index}><td>{String(row.Comparison)}</td><td>{String(row.Test)}</td><td>{pValue(row['p-value'])}</td><td>{String(row.Result)}</td></tr>)}</tbody></table></div>
      {mseRow ? <>
        <h4>Cross-validation within the reviewed training data</h4>
        <p className="section-caption">{v.cv_design.folds} folds × {v.cv_design.repeats} repeats ({v.cv_design.fitted_folds} fits, {v.cv_design.design}). The evaluation observations are never used.</p>
        <dl className="research-facts">
          <div><dt>Traditional MLR MSE</dt><dd>{format(mseRow['Baseline Mean'], 4)} ± {format(mseRow['Baseline SD'], 4)}</dd></div>
          <div><dt>Enhanced MLR MSE</dt><dd>{format(mseRow['Enhanced Mean'], 4)} ± {format(mseRow['Enhanced SD'], 4)}</dd></div>
          <div><dt>Folds where Enhanced is better</dt><dd>{format(mseRow['Folds Where Enhanced Is Better (%)'], 1)}%</dd></div>
          <div><dt>Corrected resampled t-test</dt><dd>p = {pValue(cvTest?.['p-value'])} · {String(cvTest?.Result ?? '—')}</dd></div>
        </dl>
      </> : null}
      <h4>Station classification agreement</h4>
      <p className="section-caption">Each evaluation observation is classified with its actual wait and with the Enhanced MLR predicted wait; the other six factors are the same. This shows how prediction error changes the condition, not whether the thresholds are operationally valid.</p>
      <dl className="research-facts">
        <div><dt>Resolved under both labels</dt><dd>{format(agreement['Observations resolved under both labels'], 0)} of {s.test}</dd></div>
        <div><dt>Exact agreement</dt><dd>{format(agreement['Exact agreement (%)'], 1)}%</dd></div>
        <div><dt>Within one level</dt><dd>{format(agreement['Agreement within one condition level (%)'], 1)}%</dd></div>
        <div><dt>Cohen's kappa</dt><dd>{format(agreement["Cohen's kappa"], 3)}</dd></div>
      </dl>
      {v.notes.map(note => <p key={note} className="decision-note">{note}</p>)}
    </>}
  </div></details>
}
