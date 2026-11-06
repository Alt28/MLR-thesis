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
  return <Modal title="Research documentation" close={close} canClose={!w.busy} className="wide-modal"><form onSubmit={e => {
    e.preventDefault()
    void w.configure({...s.config, research_notes: Object.fromEntries(Object.entries(notes).map(([key, value]) => [key, value.trim()]))}).then(close).catch(() => {})
  }}><div className="modal-body">
    <p className="muted">These notes are researcher declarations, not automatic verification. Saving records a new revision; analyze again to include them in the exported results.</p>
    {s.provenance?.workbook_declares_prototype && <p className="decision-note">The workbook declares prototype or simulated data. A recorded-data selection cannot override that declaration.</p>}
    <label>Data source type<select aria-label="Data source type" value={notes.source_type || 'unknown'} disabled={w.busy} onChange={e => setNotes({...notes, source_type: e.target.value})}><option value="unknown">Not documented yet</option><option value="recorded">Recorded observations (researcher declaration)</option><option value="simulated">Simulated / prototype data</option></select></label>
    <label>Dataset transport mode<select aria-label="Dataset transport mode" disabled={w.busy} value={notes.transport_mode || 'unknown'} onChange={e => setNotes({...notes, transport_mode: e.target.value})}><option value="unknown">Not specified</option><option value="bus">Bus only</option><option value="train">Train only</option><option value="mixed">Mixed bus and train</option></select><small>For mixed datasets, add a Transport Mode column containing Bus or Train for each row. Recorded row labels take precedence. This labels outputs and does not add a predictor or train separate models.</small></label>
    {fields.map(([key, label, hint]) => <label key={key}>{label}<textarea aria-label={label} aria-describedby={`research-note-${key}`} rows={2} maxLength={4000} disabled={w.busy} value={notes[key] || ''} onChange={e => setNotes({...notes, [key]: e.target.value})}/><small id={`research-note-${key}`}>{hint}</small></label>)}
    {!!s.provenance?.workbook_notes.length && <details className="disclosure"><summary>Source notes supplied with the workbook</summary><div className="disclosure-body">{s.provenance.workbook_notes.map((row, index) => <p className="section-caption" key={index}>{Object.values(row).join(' | ')}</p>)}</div></details>}
    {w.error && <p className="inline-error" role="alert">{w.error}</p>}
  </div><div className="modal-footer"><button type="button" className="button" disabled={w.busy} onClick={close}>Cancel</button><button className="button primary" disabled={w.busy}>Save research notes</button></div></form></Modal>
}

export function ControlledComparisons({s}: {s: Experiment}) {
  return <details className="disclosure controlled-comparisons"><summary>Separate data review and interaction effects</summary><div className="disclosure-body">
    {!s.study_available ? <p className="decision-note">This saved run predates the three-arm protocol. Select Analyze Dataset again to generate the additional comparison.</p> : <>
      <p className="section-caption">All three experiments use the same {s.test} test observations. A uses the original training records. B uses reviewed records. C adds selected interactions to the same reviewed records as B.</p>
      <div className="table-scroll"><table aria-label="Controlled experiment metrics"><thead><tr><th>Experiment</th><th>Training rows</th><th>MSE</th><th>RMSE (min)</th></tr></thead><tbody>{s.study_metrics?.map(row => <tr key={String(row.Arm)}><th scope="row">{String(row.Arm)}: {String(row.Model)}</th><td>{format(row['Training Rows'], 0)}</td><td>{format(row.MSE, 4)}</td><td>{format(row.RMSE, 4)}</td></tr>)}</tbody></table></div>
      <ul className="protocol-comparisons">{s.study_comparisons?.map(row => <li key={String(row.Comparison)}><strong>{String(row.Comparison)}: {String(row.Question)}</strong><span>{String(row['Outcome for second arm'])}. RMSE reduction: {format(row['RMSE reduction (min)'], 4)} min.</span></li>)}</ul>
      <p className="section-caption">Positive reductions mean lower error for the second experiment; negative values mean higher error. Flagging records alone does not demonstrate an IQR benefit. These are descriptive results from one split, not a significance test.</p>
    </>}
  </div></details>
}
