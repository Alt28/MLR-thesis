import { useEffect, useState } from 'react'
import type { Experiment, Row } from '../types'
import { LABELS, PREDICTORS } from '../types'
import { api } from '../services/api'
import { Modal, format } from './Common'
import { DataTable } from './DataTable'
import { ControlledComparisons, StatisticalChecks } from './ResearchProtocol'
import { StationCondition } from './StationCondition'

const titles = ['SOP 1: review unusual observations', 'SOP 2: model combined effects', 'SOP 3: explain station condition']

export function SOPSolutions({s, busy, onReview}: {s: Experiment | null; busy: boolean; onReview: () => void}) {
  const [open, setOpen] = useState<number | null>(null)
  const [table, setTable] = useState('bounds')
  const [row, setRow] = useState<Row | null>(null)
  const [error, setError] = useState('')
  const complete = s?.status === 'complete' && !s.classification_stale
  const terms = s ? [...s.config.pairwise_interactions, ...s.config.higher_order_interactions] : []
  const outcome = (comparison: string) => {
    const evidence = complete && s?.study_comparisons?.find(item => item.Comparison === comparison)
    return evidence ? `${evidence['Outcome for second arm']}. RMSE reduction: ${format(evidence['RMSE reduction (min)'], 4)} min.` : 'Run the analysis to evaluate this solution on recorded test waits.'
  }
  const show = (index: number) => {setTable(['bounds', 'selected_interactions', 'classification'][index]); setOpen(index)}
  useEffect(() => {
    let active = true
    setRow(null); setError('')
    if (open === 2 && complete && s) api.table(s.id, 'predictions', '', 0, 1)
      .then(data => {if (active) setRow(data.rows[0] ?? null)})
      .catch(e => {if (active) setError(e.message)})
    return () => {active = false}
  }, [open, complete, s?.id, s?.revision])

  return <section className="sop-solutions" aria-labelledby="sop-title">
    <div className="sop-heading"><span className="eyebrow">STATEMENT OF THE PROBLEM</span><h2 id="sop-title">Three SOP solutions</h2><p>See how each research problem is addressed, then inspect the evidence from the selected training dataset. Implementation alone does not prove improved accuracy.</p></div>
    <div className="sop-grid">
      <article className="panel sop-card">
        <h3>{titles[0]}</h3>
        <p><strong>Problem:</strong> unusual or incorrect training records can affect predictions.</p>
        <p><strong>Solution:</strong> IQR flags unusual values. Review each flagged record and retain, correct, or exclude it with a reason. Test records are kept separate.</p>
        <p className="sop-status">{s ? `${s.flagged} training records flagged · ${s.reviewed} reviewed · ${s.training} original / ${s.reviewed_training} reviewed training rows` : 'Upload training data to see the flags and review decisions.'}</p>
        <p className="small-text"><strong>A vs B:</strong> {outcome('A vs B')}</p>
        <button className="button small" disabled={!s || busy} onClick={() => show(0)}>View SOP 1 evidence</button>
        {!!s?.flagged && <button className="text-button" disabled={busy} onClick={onReview}>Open outlier review</button>}
      </article>
      <article className="panel sop-card">
        <h3>{titles[1]}</h3>
        <p><strong>Problem:</strong> a factor's effect may depend on another factor.</p>
        <p><strong>Solution:</strong> Enhanced MLR retains all six predictors and adds selected pairwise and higher-order interactions. Both models still use ordinary least squares.</p>
        <p className="sop-status">{s ? `${terms.length} selected combinations · ${s.approved ? 'Confirmed' : 'Awaiting confirmation'}${complete ? ' · Models fitted' : ''}` : 'Select training data to inspect its configured interaction terms.'}</p>
        <p className="small-text"><strong>B vs C:</strong> {outcome('B vs C')}</p>
        <button className="button small" disabled={!s || busy} onClick={() => show(1)}>View SOP 2 evidence</button>
      </article>
      <article className="panel sop-card">
        <h3>{titles[2]}</h3>
        <p><strong>Problem:</strong> a waiting-time estimate alone does not explain the station condition.</p>
        <p><strong>Solution:</strong> {(s?.config.category_scoring ?? 'automatic') === 'automatic' ? 'Station and calendar categories are scored automatically from their mean training wait against the training wait quartiles (approved manual mappings take precedence). Average the seven scores and apply the configured condition thresholds.' : s?.config.classification_approved ? 'Use the documented, approved category mappings and numerical rules. Average seven complete scores and apply the configured condition thresholds.' : 'The seven-factor framework is retained, pending documented approval of station and calendar mappings. No category scores are inferred.'}</p>
        <p className="sop-status">{complete && s ? `${s.test} test observations checked · ${s.test - LABELS.reduce((total, label) => total + (s.distribution[label] || 0), 0)} need a decision` : 'Train the models to see observation scores and station summaries.'}</p>
        <p className="small-text">Unresolved factors remain unresolved. These rules do not independently prove a station's real-world condition.</p>
        <button className="button small" disabled={!s || busy} onClick={() => show(2)}>View SOP 3 evidence</button>
      </article>
    </div>
    {open !== null && s && <Modal title={titles[open]} close={() => setOpen(null)} className="wide-modal sop-evidence"><div className="modal-body">
      <p className="section-caption">Dataset: {s.name} · revision {s.revision}. These are training/evaluation records; new prediction uploads do not change this evidence.</p>
      {open === 0 && <>
        <p>IQR means interquartile range: Q3 − Q1, the spread of the middle half of the training values. Values below Q1 − {s.config.iqr_multiplier} × IQR or above Q3 + {s.config.iqr_multiplier} × IQR are flagged for review. A flag is not an automatic deletion.</p>
        <p><strong>Applied to:</strong> {s.config.iqr_columns.join(', ')}. The limits are learned from training records only.</p>
        <label>Review evidence<select aria-label="SOP 1 evidence table" value={table} onChange={e => setTable(e.target.value)}><option value="bounds">IQR limits</option><option value="flags">Flagged observations</option><option value="audit">Review decisions and reasons</option></select></label>
        <DataTable key={table} s={s} name={table}/>
        <p>A uses original training records; B uses reviewed records with the same additive model. If no records were corrected or excluded, A and B cannot demonstrate a review benefit.</p>
      </>}
      {open === 1 && <>
        <p>Traditional MLR adds each predictor's contribution. Enhanced MLR also multiplies selected factors so that their effects can depend on each other. The product terms are derived from the original six predictors; Actual Waiting Time is never an input.</p>
        <p><strong>Main effects kept in both models:</strong> {PREDICTORS.join(', ')}.</p>
        <h3>Selected combinations</h3>
        {terms.length ? <ul className="sop-terms">{terms.map(term => <li key={term.join('|')}>{term.join(' × ')}</li>)}</ul> : <p>No interactions selected.</p>}
        <p>{s.config.hierarchical_interactions ? 'Hierarchy is enabled: lower-order combinations required by a selected higher-order term are included.' : 'Interaction hierarchy is disabled for this configuration.'} {s.config.center_interactions ? 'Product factors are centered using training means.' : 'Products use uncentered factors.'}</p>
        {complete && <><label>Model evidence<select aria-label="SOP 2 evidence table" value={table} onChange={e => setTable(e.target.value)}><option value="selected_interactions">Selected and included terms</option><option value="coefficients">Fitted coefficients for both models</option><option value="diagnostics">Model diagnostics</option></select></label><DataTable key={table} s={s} name={table}/></>}
        <p>B and C use the same reviewed training data and the same test rows. Lower error for C supports an interaction benefit for this dataset; equal or higher error does not.</p>
      </>}
      {(open === 0 || open === 1) && complete && <><ControlledComparisons s={s}/><StatisticalChecks s={s}/></>}
      {open === 2 && <>
        <p>The overall score is (six predictor severities + predicted-wait severity) ÷ 7. Scores range from 0 (normal) to 3 (severe). Current overall boundaries: {s.config.station_thresholds.join(', ')}. Predicted-wait boundaries: {s.config.wait_thresholds.join(', ')} minutes.</p>
        <p>Missing units, unresolved directions, unknown categories, or insufficient variation can leave a factor unresolved. The system then reports Requires Researcher Decision instead of filling in a score.</p>
        {complete ? <>
          <p>Select an observation to inspect its seven scores and the rule used for each.</p>
          <DataTable s={s} name="classification" columns={['Record ID', 'Enhanced Predicted Waiting Time', 'Overall Station Classification', 'Multi-Factor Station Score']} onRow={setRow} actionLabel="Explain scores"/>
          {error && <p className="inline-error" role="alert">{error}</p>}
          {row && <><p className="observation-label">Observation <strong>{String(row['Record ID'])}</strong></p><StationCondition s={s} row={row} expanded/></>}
        </> : <p>Analyze the training dataset to calculate predictions and observation scores.</p>}
        <details className="disclosure"><summary>Training thresholds and category evidence</summary><div className="disclosure-body"><DataTable s={s} name="thresholds"/><DataTable s={s} name="evidence"/></div></details>
        {complete && s.station_aggregation.available && <details className="disclosure"><summary>Station summaries from evaluation records</summary><div className="disclosure-body"><DataTable s={s} name="station_summary"/></div></details>}
      </>}
    </div></Modal>}
  </section>
}
