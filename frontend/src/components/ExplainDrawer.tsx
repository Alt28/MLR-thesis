import type { ReactNode } from 'react'
import { BusFront, CalendarDays, CalendarRange, ChevronLeft, ChevronRight, Clock3, Gauge, MapPin, UsersRound } from 'lucide-react'
import type { Cell, Experiment, Row } from '../types'
import { CATEGORICAL, LABELS, TARGET } from '../types'
import { Modal } from './Common'
import { StationCondition } from './StationCondition'
import { station, when } from './PredictionTable'

const SEVERITIES = ['Normal', 'Minor', 'Moderate', 'Severe']
const TONES = ['normal', 'minor', 'moderate', 'severe']
const FACTORS: {key: string; label: string; icon: ReactNode}[] = [
  {key: 'Passenger Volume', label: 'Passenger Volume', icon: <UsersRound size={17}/>},
  {key: 'Vehicle Frequency', label: 'Vehicle Frequency', icon: <BusFront size={17}/>},
  {key: 'Station / Stop', label: 'Station / Stop', icon: <MapPin size={17}/>},
  {key: 'Time of Day', label: 'Time of Day', icon: <Clock3 size={17}/>},
  {key: 'Day of Week', label: 'Day of Week', icon: <CalendarDays size={17}/>},
  {key: 'Month of Year', label: 'Month of Year', icon: <CalendarRange size={17}/>},
  {key: 'Predicted Waiting Time', label: 'Predicted wait (Enhanced)', icon: <Gauge size={17}/>},
]
const num = (v: Cell) => typeof v === 'number' && Number.isFinite(v) ? v : null
const fmt = (v: Cell, d = 2) => { const n = num(v); return n === null ? '—' : n.toLocaleString(undefined, {maximumFractionDigits: d}) }
const sev = (v: Cell) => typeof v === 'number' && Number.isInteger(v) && v >= 0 && v <= 3 ? v : null

// Plain-language reading of the saved classifier rules; nothing is recomputed in the browser.
function reason(s: Experiment, row: Row, factor: string, score: number | null): string {
  if (factor === 'Predicted Waiting Time') {
    const [a, b, c] = s.config.wait_thresholds
    const bands = [`${a} min or less`, `over ${a} up to ${b} min`, `over ${b} up to ${c} min`, `over ${c} min`]
    return score === null ? 'Not scored.' : `${fmt(row['Enhanced Predicted Waiting Time'])} min falls in the “${bands[score]}” band.`
  }
  if (CATEGORICAL.includes(factor)) {
    const category = String(row[factor] ?? '')
    const e = s.evidence.find(x => x.Factor === factor && x.Category === category)
    if (!e || score === null) return `“${category}” was not seen in training, so it cannot be scored.`
    return `In training, “${category}” averaged ${fmt(e['Mean Actual Wait'])} min of waiting (middle half of all waits: ${fmt(e.Q1, 1)}–${fmt(e.Q3, 1)} min).`
  }
  const q = s.thresholds.find(t => t.Factor === factor)
  const value = num(row[factor])
  if (!q || value === null || score === null) return 'Not scored.'
  if (String(q['Direction Source'] ?? '').startsWith('No detectable')) return 'No clear effect on waiting time in training, so it always counts as Normal.'
  const [q1, q2, q3] = [num(q.Q1), num(q.Q2), num(q.Q3)]
  const level = q1 !== null && value <= q1 ? 'low' : q2 !== null && value <= q2 ? 'below average' : q3 !== null && value <= q3 ? 'above average' : 'high'
  const unit = factor === 'Passenger Volume' ? 'passengers' : 'per hour'
  const rule = q.Direction === 'lower' ? 'fewer means longer waits' : 'more means longer waits'
  return `${level[0].toUpperCase()}${level.slice(1)} compared with training (middle half: ${fmt(q1, 0)}–${fmt(q3, 0)} ${unit}); ${rule}.`
}

function Meter({score}: {score: number | null}) {
  return <span className={`explain-meter tone-${score === null ? 'none' : TONES[score]}`} aria-hidden>
    {[0, 1, 2, 3].map(i => <i key={i} className={score !== null && i <= score ? 'on' : ''}/>)}
  </span>
}

export function ExplainDrawer({s, rows, position, onMove, close}: {
  s: Experiment; rows: Row[]; position: number; onMove: (position: number) => void; close: () => void
}) {
  const row = rows[position]
  const score = num(row['Multi-Factor Station Score'])
  const label = score === null ? 'Requires Researcher Decision' : String(row['Overall Station Classification'])
  const band = LABELS.indexOf(label)
  const tone = band < 0 ? 'none' : TONES[band]
  const scores = FACTORS.map(f => sev(row[`${f.key} Severity`]))
  const bounds = [0, ...s.config.station_thresholds, 3]
  const actual = num(row[TARGET])
  const unit = (f: string) => f === 'Passenger Volume' ? 'passengers' : f === 'Vehicle Frequency' ? 'vehicles/hour' : f === 'Predicted Waiting Time' ? 'min' : ''
  const value = (f: string) => f === 'Predicted Waiting Time' ? fmt(row['Enhanced Predicted Waiting Time'])
    : f === 'Station / Stop' ? station(row) : typeof row[f] === 'number' ? fmt(row[f], 0) : String(row[f] ?? '—')
  const go = (p: number) => { if (p >= 0 && p < rows.length) onMove(p) }

  return <Modal title={station(row)} close={close} className="explain-drawer">
    <div className="modal-body explain-body" onKeyDown={e => {
      if (e.key === 'ArrowLeft') go(position - 1)
      if (e.key === 'ArrowRight') go(position + 1)
    }}>
      <div className="explain-nav">
        <div><span>{when(row)}</span><code title={String(row['Record ID'] ?? '')}>{String(row['Record ID'] ?? '')}</code></div>
        <div className="explain-steps">
          <button type="button" className="icon-button" aria-label="Previous observation" disabled={position === 0} onClick={() => go(position - 1)}><ChevronLeft size={17}/></button>
          <span>{position + 1} of {rows.length}</span>
          <button type="button" className="icon-button" aria-label="Next observation" disabled={position >= rows.length - 1} onClick={() => go(position + 1)}><ChevronRight size={17}/></button>
        </div>
      </div>

      <section className={`explain-hero tone-${tone}`} aria-label="Station condition">
        <span className="explain-eyebrow">Station condition</span>
        <strong className="explain-label">{label}</strong>
        <div className="explain-gauge" role="img" aria-label={`Multi-Factor Score ${score === null ? 'not available' : score.toFixed(2)} out of 3`}>
          <div className="explain-track">{LABELS.map((name, i) => <span key={name} className={`seg tone-${TONES[i]}${i === band ? ' current' : ''}`}
            style={{flexGrow: bounds[i + 1] - bounds[i]}} title={`${name}: ${bounds[i].toFixed(2)}–${bounds[i + 1].toFixed(2)}`}/>)}</div>
          {score !== null && <span className="explain-marker" style={{left: `${(score / 3) * 100}%`}}><b>{score.toFixed(2)}</b></span>}
          <div className="explain-scale">{LABELS.map((name, i) => <span key={name} style={{flexGrow: bounds[i + 1] - bounds[i]}}>{name.replace(' Operation', '').replace(' Delay', '')}</span>)}</div>
          <div className="explain-ends"><span>0</span><span>3</span></div>
        </div>
      </section>

      <div className="explain-values">
        <div><span>Traditional MLR</span><strong>{fmt(row['Baseline Predicted Waiting Time'])}<small> min</small></strong></div>
        <div className="enhanced"><span>Enhanced MLR</span><strong>{fmt(row['Enhanced Predicted Waiting Time'])}<small> min</small></strong></div>
        {actual !== null && <div><span>Actual wait</span><strong>{fmt(actual)}<small> min</small></strong></div>}
      </div>

      <section aria-label="Seven factors">
        <h3 className="explain-title">Why this condition?</h3>
        <p className="explain-hint">Each factor scores from 0 (Normal) to 3 (Severe), using rules learned from the training data.</p>
        <ul className="explain-factors">{FACTORS.map((f, i) => <li key={f.key}>
          <span className="explain-icon">{f.icon}</span>
          <div className="explain-copy">
            <div className="explain-row"><strong>{f.label}</strong><span className="explain-value">{value(f.key)}{unit(f.key) && <small> {unit(f.key)}</small>}</span></div>
            <p>{reason(s, row, f.key, scores[i])}</p>
          </div>
          <div className="explain-score"><Meter score={scores[i]}/><span className={`explain-pill tone-${scores[i] === null ? 'none' : TONES[scores[i]!]}`}>{scores[i] === null ? 'Unresolved' : SEVERITIES[scores[i]!]}</span></div>
        </li>)}</ul>
      </section>

      <div className="explain-sum">
        <span>Multi-Factor Score</span>
        <div>{scores.map((v, i) => <b key={i} className={`tone-${v === null ? 'none' : TONES[v]}`}>{v ?? '—'}</b>)}</div>
        <strong>{score === null ? 'Not available' : `(${scores.join(' + ')}) ÷ 7 = ${score.toFixed(2)}`}</strong>
      </div>

      <details className="disclosure explain-technical">
        <summary>Technical details (quartiles, coefficients, rule sources)</summary>
        <div className="disclosure-body"><StationCondition s={s} row={row} expanded/></div>
      </details>
    </div>
  </Modal>
}
