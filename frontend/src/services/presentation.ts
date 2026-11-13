// Presentation names only. Existing scientific artifact keys remain compatible.
const columnLabels: Record<string, string> = {
  'Overall Station Classification': 'Station Condition',
  'Multi-Factor Station Score': 'Multi-Factor Score (0–3)',
  'Baseline Predicted Waiting Time': 'Traditional MLR Prediction',
  'Enhanced Predicted Waiting Time': 'Enhanced MLR Prediction',
  'Baseline Error (actual - predicted)': 'Traditional Prediction Error',
  'Enhanced Error (actual - predicted)': 'Enhanced Prediction Error',
}
export const columnLabel = (name: string) => columnLabels[name] ?? name.replace(/^Baseline/, 'Traditional')

const predictionErrorHelp = 'Actual Waiting Time − Predicted Waiting Time. Negative = model predicted too high. Positive = model predicted too low. Closer to 0 = closer prediction for that observation.'
export const columnHelp: Record<string, string> = {
  'Actual Waiting Time': 'Recorded waiting time from the dataset.',
  'Baseline Predicted Waiting Time': 'Prediction produced by the baseline additive MLR.',
  'Enhanced Predicted Waiting Time': 'Prediction produced by MLR with the selected interaction terms.',
  'Prediction Error': predictionErrorHelp,
  'Baseline Error (actual - predicted)': predictionErrorHelp,
  'Enhanced Error (actual - predicted)': predictionErrorHelp,
  'RMSE': 'Square root of the mean squared error, in minutes. It weights larger errors more heavily than a plain average error. Lower is better.',
  'Multi-Factor Station Score': 'Combined operational severity score from the six transportation predictors and the Enhanced MLR predicted waiting time.',
  'Overall Station Classification': 'Station condition based on Traffic Condition, Weather Condition, Passenger Volume, Route Distance, Vehicle Frequency, Time of Day, and Enhanced MLR Predicted Waiting Time.',
}

// Keep the backend's metric comparison and effective-equality rule authoritative.
export const performanceConclusion = (conclusion: string | null) => {
  if (conclusion === 'Enhanced MLR has lower held-out MSE and RMSE in this experiment.') return 'Enhanced MLR produced lower prediction error in this experiment.'
  if (conclusion === 'Enhanced MLR has higher held-out MSE and RMSE in this experiment.') return 'Traditional MLR produced lower prediction error in this experiment.'
  return conclusion?.replaceAll('Baseline', 'Traditional').replaceAll('baseline', 'traditional')
}
export const displayValue = (value: unknown) => value === 'Baseline MLR' ? 'Traditional MLR' : value === 'Pending configuration' ? 'Requires Researcher Decision' : value === 'retain_unreviewed' ? 'Retain (default)' : value

export function friendlyError(value: string, context: 'dataset' | 'analysis' = 'analysis') {
  const message = value.replace(/^Could not import the dataset:\s*/, '')
  const missing = message.match(/Missing required columns:\s*(.+)/)
  if (missing) {
    const columns = missing[1].split(',').map(name => name.trim())
    return columns.length === 1 ? `${columns[0]} is missing from your dataset. Add that column and try again.`
      : `These columns are missing: ${columns.join(', ')}. Check the column names and upload the file again.`
  }
  const invalid = message.match(/^([^:]+): (missing values|empty category values|all values must be numerical|values must be finite and nonnegative)/)
  if (invalid) return `${invalid[1]} ${invalid[2].startsWith('all values') ? 'must contain numbers' : invalid[2].startsWith('values must') ? 'must contain valid numbers of zero or more' : 'contains blank values'}. Correct the file and upload it again.`
  if (/no observations/.test(message)) return 'This file is empty. Add recorded observations to the template, then upload it again.'
  if (/At least 10/.test(message)) return 'This file needs at least 10 observations before analysis can run. Add recorded data and try again.'
  if (/Duplicate column names/.test(message)) return 'Some columns have the same name. Give each required column a unique name and upload the file again.'
  if (/Record IDs/.test(message)) return 'Each observation needs a unique, non-empty Record ID. Check that column and try again.'
  if (/25 MB|too large|size limit/i.test(message)) return 'This file is too large. Upload a CSV or XLSX file smaller than 25 MB.'
  if (/changed in another tab|revision|stale/i.test(message)) return 'The dataset changed in another tab. Refresh this page before trying again.'
  if (/connect to Transit Lab/.test(message)) return message
  if (context === 'dataset') return "We couldn't read this file. Check the required columns, save it as CSV or XLSX, and try again."
  return "We couldn't complete the analysis. Check your data and saved settings, then try again."
}
