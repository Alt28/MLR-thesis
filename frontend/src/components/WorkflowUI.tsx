import { ArrowRight, ChartNoAxesCombined, Check, GitBranch, Layers3 } from 'lucide-react'

export function WorkflowHeading({stage, current}: {stage: 'training' | 'prediction'; current: number}) {
  const training = stage === 'training'
  const steps = training ? ['Add recorded data', 'Set up the models', 'Compare accuracy'] : ['Add new observations', 'Choose trained models', 'Compare predictions']
  return <div className="workflow-heading">
    <div className="workflow-title-row"><div><span className="eyebrow">{training ? 'BUILD YOUR MODELS' : 'PUT YOUR MODELS TO WORK'}</span><h1>{training ? 'Model training' : 'Test & predict'}</h1><p>{training ? 'Learn from recorded waiting times. See how both models perform.' : 'Upload new bus or train observations and compare their predicted waiting times.'}</p></div><span className="page-purpose">{training ? <Layers3 size={16}/> : <GitBranch size={16}/>}<span>{training ? 'Actual waits required' : 'Actual waits can be blank'}</span></span></div>
    <ol className="workflow-progress" aria-label={training ? 'Training steps' : 'Prediction steps'}>{steps.map((label, i) => <li key={label} className={current > i + 1 ? 'done' : current === i + 1 ? 'current' : ''} aria-current={current === i + 1 ? 'step' : undefined}><span>{current > i + 1 ? <Check size={14}/> : `0${i + 1}`}</span><strong>{label}</strong>{i < 2 && <ArrowRight size={15}/>}</li>)}</ol>
  </div>
}

export function ComparisonEmpty({stage, error}: {stage: 'training' | 'prediction'; error?: string}) {
  return <div className="comparison-empty" role="status"><div className="comparison-empty-copy"><span className="empty-chart-icon"><ChartNoAxesCombined size={26}/></span><h3>{error ? 'Check your training setup' : 'Ready when your data is'}</h3><p>{error || (stage === 'training' ? 'Upload recorded examples, review the setup, then train both models. Their accuracy results will appear here.' : 'Choose a trained model and upload the six predictors. Both waiting-time estimates will appear side by side.')}</p></div><div className="model-pair" aria-label="Models compared"><div><span className="model-dot"/><strong>Traditional MLR</strong><small>Individual predictor effects</small></div><span className="model-pair-vs">vs</span><div><span className="model-dot enhanced"/><strong>Enhanced MLR</strong><small>Predictors + interaction terms</small></div></div></div>
}
