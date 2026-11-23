import type { Row } from '../types'
import { TARGET } from '../types'

const num = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : null
const fixed = (value: unknown, digits = 2) => { const n = num(value); return n === null ? '—' : n.toFixed(digits) }

const TONES: Record<string, string> = {
  'Normal Operation': 'normal', 'Minor Delay': 'minor', 'Moderate Delay': 'moderate', 'Severe Delay': 'severe',
}

export function when(row: Row) {
  const raw = row['Observation Hour Local']
  if (typeof raw === 'string' && raw.length >= 13) {
    const date = new Date(raw.replace(' ', 'T'))
    if (!Number.isNaN(date.getTime())) {
      const day = date.toLocaleDateString('en-US', {weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'})
      return `${day} · ${raw.slice(11, 16)}`
    }
  }
  return [row['Day of Week'], row['Month of Year'], row['Time of Day']].filter(Boolean).join(' · ')
}

export function station(row: Row) {
  return String(row['Station / Stop'] ?? '').replace(/^MTA Subway Complex /, 'Complex ')
}

function Prediction({value, error, better}: {value: unknown; error: unknown; better: boolean}) {
  const e = num(error)
  return <div className={`pt-prediction${better ? ' better' : ''}`}>
    <strong>{fixed(value)}</strong>
    <small title="Actual minus predicted, in minutes">{e === null ? '' : `error ${e > 0 ? '+' : ''}${e.toFixed(2)}`}</small>
  </div>
}

export function Condition({label, score}: {label: unknown; score: unknown}) {
  const text = String(label ?? '')
  const s = num(score)
  const tone = TONES[text]
  if (!tone) return <span className="pt-condition pending" title={text}>Not classified</span>
  return <div className={`pt-condition ${tone}`}>
    <span className="pt-pill">{text.replace(' Operation', '')}</span>
    {s !== null && <span className="pt-score" title="Multi-Factor Score, 0–3"><span className="pt-bar"><span style={{width: `${(s / 3) * 100}%`}}/></span>{s.toFixed(2)}</span>}
  </div>
}

export function PredictionRows({rows, onRow, actionLabel}: {rows: Row[]; onRow?: (row: Row) => void; actionLabel: string}) {
  return <table className="prediction-table" aria-label="Prediction results">
    <colgroup><col className="pt-col-obs"/><col className="pt-col-num"/><col className="pt-col-num"/><col className="pt-col-num"/><col className="pt-col-closer"/><col className="pt-col-cond"/>{onRow && <col className="pt-col-action"/>}</colgroup>
    <thead><tr>
      <th>Observation</th>
      <th className="num" title="Recorded waiting time, minutes">Actual (min)</th>
      <th className="num" title="Traditional MLR prediction, minutes">Traditional (min)</th>
      <th className="num" title="Enhanced MLR prediction, minutes">Enhanced (min)</th>
      <th title="Model whose prediction is closer to the actual wait">Closer model</th>
      <th title="Seven-factor station condition and Multi-Factor Score (0–3)">Station condition</th>
      {onRow && <th><span className="visually-hidden">Details</span></th>}
    </tr></thead>
    <tbody>{rows.map((row, i) => {
      const id = String(row['Record ID'] ?? '')
      const base = num(row['Baseline Error (actual - predicted)'])
      const enh = num(row['Enhanced Error (actual - predicted)'])
      const closer = base === null || enh === null ? null : Math.abs(enh) < Math.abs(base) ? 'Enhanced' : Math.abs(base) < Math.abs(enh) ? 'Traditional' : 'Tie'
      return <tr key={id || i}>
        <td><div className="pt-obs"><code title={id}>{id.length > 16 ? `${id.slice(0, 14)}…` : id}</code><strong>{station(row)}</strong><small>{when(row)}</small></div></td>
        <td className="num"><strong className="pt-actual">{fixed(row[TARGET])}</strong></td>
        <td className="num"><Prediction value={row['Baseline Predicted Waiting Time']} error={base} better={closer === 'Traditional'}/></td>
        <td className="num"><Prediction value={row['Enhanced Predicted Waiting Time']} error={enh} better={closer === 'Enhanced'}/></td>
        <td>{closer && <span className={`pt-closer ${closer.toLowerCase()}`}>{closer}</span>}</td>
        <td><Condition label={row['Overall Station Classification']} score={row['Multi-Factor Station Score']}/></td>
        {onRow && <td className="pt-action"><button className="text-button" onClick={() => onRow(row)}>{actionLabel} <span aria-hidden>↗</span></button></td>}
      </tr>
    })}</tbody>
  </table>
}
