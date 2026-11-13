import { columnHelp, columnLabel } from '../services/presentation'

const fields = ['Actual Waiting Time', 'Baseline Predicted Waiting Time', 'Enhanced Predicted Waiting Time', 'Prediction Error', 'Multi-Factor Station Score']

export function PredictionExplanations() {
  return <dl className="metric-explanations prediction-explanations" aria-label="Prediction explanations">
    {fields.map(field => <div key={field}><dt>{columnLabel(field)}</dt><dd>{columnHelp[field]}</dd></div>)}
  </dl>
}
