import type { Experiment, Row } from '../types'
import { CATEGORICAL, LABELS, PREDICTORS } from '../types'
import { format } from './Common'

const DECISION = 'Requires Researcher Decision'
const INSUFFICIENT = 'Insufficient Variation for Classification'
const SEVERITIES = ['Normal', 'Minor', 'Moderate', 'Severe']
const FACTORS = [...PREDICTORS, 'Predicted Waiting Time']
const fixed = (value: unknown, digits = 2) => typeof value === 'number' && Number.isFinite(value)
  ? value.toLocaleString(undefined, {minimumFractionDigits: digits, maximumFractionDigits: digits}) : '—'
const severityScore = (value: unknown) => typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 3 ? value : null

// Explain the saved classifier output; never fit thresholds or classify again in the browser.
function factorRule(s: Experiment, row: Row, factor: string, score: number | null) {
  if (CATEGORICAL.includes(factor)) {
    const category = String(row[factor])
    const evidence = s.evidence.find(e => e.Factor === factor && e.Category === category)
    if (!evidence) return {condition: DECISION, source: `“${category}” has no training evidence or configured mapping.`}
    const mean = evidence['Training Count'] ? `Training category mean = ${format(evidence['Mean Actual Wait'], 6)} minutes.` : 'No training observations for this configured category.'
    const quartiles = `Training Actual Waiting Time Q1 = ${format(evidence.Q1, 6)} · Q2 (median) = ${format(evidence.Q2, 6)} · Q3 = ${format(evidence.Q3, 6)} minutes.`
    const configured = evidence['Mapping Source'] === 'Researcher configuration'
    const source = `${mean} ${quartiles} ${configured ? 'Researcher-approved category mapping; overrides the derived score.' : 'Training category mean compared with training waiting-time quartiles; higher mean → higher severity.'}`
    if (score == null) return {condition: String(row[`${factor} Classification Status`] || DECISION), source}
    const ranges = [
      `Mean ≤ ${format(evidence.Q1, 6)} (Q1)`,
      `${format(evidence.Q1, 6)} (Q1) < mean ≤ ${format(evidence.Q2, 6)} (Q2)`,
      `${format(evidence.Q2, 6)} (Q2) < mean ≤ ${format(evidence.Q3, 6)} (Q3)`,
      `Mean > ${format(evidence.Q3, 6)} (Q3)`,
    ]
    return {condition: configured ? `“${category}” → ${SEVERITIES[score]} / ${score}` : ranges[score], source}
  }
  if (factor === 'Predicted Waiting Time') {
    const [a, b, c] = s.config.wait_thresholds
    const ranges = [`≤ ${format(a)} minutes`, `> ${format(a)} to ≤ ${format(b)} minutes`, `> ${format(b)} to ≤ ${format(c)} minutes`, `> ${format(c)} minutes`]
    return {
      condition: score == null ? DECISION : ranges[score],
      source: Number(row['Enhanced Predicted Waiting Time']) < 0
        ? `Classification uses ${format(row['Waiting Time Used for Classification'])} minutes; the original negative prediction is retained for evaluation.`
        : 'Waiting-time severity · one of seven factors',
    }
  }
  const q = s.thresholds.find(t => t.Factor === factor)
  if (!q || !['Q1', 'Q2', 'Q3'].every(k => typeof q[k] === 'number')) {
    return {condition: DECISION, source: 'Training quartiles unavailable.'}
  }
  const quartiles = `Training Q1 = ${format(q.Q1, 6)} · Q2 (median) = ${format(q.Q2, 6)} · Q3 = ${format(q.Q3, 6)}`
  if (q.Status === INSUFFICIENT) return {condition: INSUFFICIENT, source: `${quartiles}. Constant/effectively constant values or collapsed quartiles; no severity assigned, even with a configured direction.`}
  if (score == null || !['higher', 'lower'].includes(String(q.Direction))) {
    return {condition: DECISION, source: `${quartiles}. No configured direction or usable training relationship with Actual Waiting Time.`}
  }
  const bin = q.Direction === 'lower' ? 3 - score : score
  const ranges = [
    `Value ≤ ${format(q.Q1, 6)} (Q1)`,
    `${format(q.Q1, 6)} (Q1) < value ≤ ${format(q.Q2, 6)} (Q2)`,
    `${format(q.Q2, 6)} (Q2) < value ≤ ${format(q.Q3, 6)} (Q3)`,
    `Value > ${format(q.Q3, 6)} (Q3)`,
  ]
  return {condition: ranges[bin], source: `${quartiles}. ${q.Direction === 'lower' ? 'Lower' : 'Higher'} values → higher severity. ${q['Direction Source']}; training Pearson r = ${format(q['Training Pearson Correlation'], 6)}.`}
}

export function StationCondition({s, row, summaryOnly = false}: {s: Experiment; row: Row; summaryOnly?: boolean}) {
  const score = typeof row['Multi-Factor Station Score'] === 'number' ? row['Multi-Factor Station Score'] : null
  const label = score == null ? DECISION : String(row['Overall Station Classification'])
  const band = score == null ? -1 : LABELS.indexOf(label)
  const scores = FACTORS.map(f => severityScore(row[`${f} Severity`]))
  const bounds = [0, ...s.config.station_thresholds, 3]
  const waitBounds = s.config.wait_thresholds
  const waitRanges = [`≤ ${format(waitBounds[0])}`, `> ${format(waitBounds[0])} to ≤ ${format(waitBounds[1])}`, `> ${format(waitBounds[1])} to ≤ ${format(waitBounds[2])}`, `> ${format(waitBounds[2])}`]
  const unit = (factor: string) => factor === 'Predicted Waiting Time' ? 'minutes'
    : factor === 'Route Distance' ? s.config.route_distance_unit
    : factor === 'Vehicle Frequency' ? s.config.vehicle_frequency_unit
    : factor === 'Passenger Volume' ? 'passengers' : ''

  if (summaryOnly) return <section className={`station-brief station-band-${band}`} aria-label="Station Condition">
    <h3>Station Condition</h3>
    <div className="station-condition"><strong className={score == null ? 'unresolved-condition' : 'condition-label'}>{label}</strong></div>
    <p className="sr-only" role="status">Observation {String(row['Record ID'])}: {label}.</p>
  </section>

  return <section className={`station-section station-band-${band}`} aria-label="Station Condition">
    <div className="station-heading"><h3>Station Condition</h3></div>
    <div className="station-summary">
      <div className="station-condition"><span>Overall Station Condition</span><strong className={score == null ? 'unresolved-condition' : 'condition-label'}>{label}</strong></div>
      <div className="station-score"><span>Multi-Factor Score</span><strong title={score == null ? DECISION : String(score)}>{fixed(score)}</strong><small>out of 3.00</small></div>
    </div>
    <p className="station-context">Based on the predicted wait and six transportation factors for this observation.</p>
    <p className="sr-only" role="status">Observation {String(row['Record ID'])}: {label}. Multi-factor score {fixed(score)}.</p>
    {score == null && <p className="decision-note">View Threshold Details for the unresolved factors. Constant variables require suitable varied observations; changing a direction cannot create variation. Undefined rules or units can be reviewed in Advanced Settings.</p>}
    <details className="disclosure classification-details">
      <summary>View Threshold Details</summary>
      <div className="disclosure-body">
        <p className="section-caption station-observation">Observation <strong>{String(row['Record ID'])}</strong> · Enhanced prediction + six transportation factors</p>
        {score == null && <p className="decision-note">{DECISION}: {String(row['Missing Classification Definitions'])}.</p>}
        <p className="threshold-source">All quartiles, category means, and inferred directions use reviewed training data only. Explicit configured mappings take precedence. A correlation direction describes this training sample; it is not a significance or causality claim.</p>
        <div className="table-scroll threshold-scroll" tabIndex={0} aria-label="Seven-factor threshold breakdown; scroll horizontally for all columns">
          <table aria-label="Classification factors">
            <thead><tr><th>Factor</th><th>Value</th><th>Condition</th><th>Severity Score</th></tr></thead>
            <tbody>{FACTORS.map((factor, i) => {
              const severity = scores[i]
              const rule = factorRule(s, row, factor, severity)
              return <tr key={factor}>
                <th scope="row"><small className="factor-index">S{i + 1}</small>{factor === 'Predicted Waiting Time' ? 'Enhanced MLR Predicted Waiting Time' : factor}</th>
                <td className="factor-value">{format(row[factor === 'Predicted Waiting Time' ? 'Enhanced Predicted Waiting Time' : factor], 6)}{unit(factor) && <small>{unit(factor)}</small>}</td>
                <td className="factor-rule"><span>{rule.condition}</span><small>{rule.source}</small></td>
                <td><span className={`severity-label severity-${severity ?? 'pending'}`}>{severity == null ? String(row[`${factor} Classification Status`] || DECISION) : SEVERITIES[severity]}</span><strong className="factor-score">{severity ?? '—'}</strong></td>
              </tr>
            })}</tbody>
            <tfoot><tr><th colSpan={2} scope="row">Multi-Factor Score<strong className="breakdown-score" title={score == null ? DECISION : String(score)}>{score == null ? '—' : fixed(score, 6)}<small> / 3</small></strong></th><td colSpan={2}><span>Final Station Condition</span><strong>{label}</strong></td></tr></tfoot>
          </table>
        </div>
        <div className="score-calculation"><p>Multi-Factor Station Score = (S1 + S2 + S3 + S4 + S5 + S6 + S7) / 7</p><strong>{score == null ? 'All seven severity scores and required definitions must be available.' : `(${scores.join(' + ')}) / 7 = ${fixed(score, 6)}`}</strong><small>Every factor has weight 1/7. The final condition uses the unrounded score.</small></div>
        <ul className="station-bands" aria-label="Final station classification bands">{LABELS.map((name, i) => <li key={name} className={band === i ? 'current-band' : ''} aria-current={band === i ? 'true' : undefined}><span>{fixed(bounds[i])} to {i === 3 ? '' : '<'}{fixed(bounds[i + 1])}</span><strong>{name}</strong>{band === i && <small>Selected condition</small>}</li>)}</ul>
        <div className="waiting-bands"><h4>Predicted waiting-time severity</h4><ul>{SEVERITIES.map((name, i) => <li key={name}><span>{waitRanges[i]} minutes</span><strong>{name} / {i}</strong></li>)}</ul></div>
      </div>
    </details>
  </section>
}
