import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Check, Database, LoaderCircle, Play, SlidersHorizontal } from 'lucide-react'
import type { Workspace } from '../hooks/useExperiment'
import { DatasetInput } from '../components/DatasetInput'
import { AnalysisSettings, ConfirmInteractions } from '../components/AnalysisSettings'
import { IQRReview } from '../components/IQRReview'
import { AnalysisResults } from '../components/AnalysisResults'
import { LoadingBus } from '../components/LoadingBus'
import { friendlyError } from '../services/presentation'
import { api } from '../services/api'
import type { PredictionDataset } from '../components/PredictionOnly'
import { SOPSolutions } from '../components/SOPSolutions'
import { WorkflowHeading, ComparisonEmpty } from '../components/WorkflowUI'

export function AnalysisPage({w, onPredictionDataset}: {w: Workspace; onPredictionDataset: (dataset: PredictionDataset) => void}) {
  const s = w.experiment
  const [rejected, setRejected] = useState('')
  const [step, setStep] = useState('')
  const [approved, setApproved] = useState(false)
  const [checking, setChecking] = useState(false)
  const inspecting = useRef(false)
  const resultPanel = useRef<HTMLElement>(null)
  const wasAnalyzing = useRef(false)
  const busy = w.busy || checking
  const analyzing = w.operation === 'analyze' || s?.status === 'running'
  const inputWorkspace = {...w, busy, operation: checking ? 'upload' as const : w.operation}
  const declarationsReady = !!s?.config.observed_targets_confirmed && !!s?.config.prediction_inputs_available
  useEffect(() => {setApproved(false); setStep(''); setRejected('')}, [s?.id])
  useEffect(() => {
    if (wasAnalyzing.current && !analyzing && s?.export_ready && s.status === 'complete') {
      const panel = resultPanel.current
      if (panel && !panel.closest('[hidden]')) panel.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'})
    }
    wasAnalyzing.current = analyzing
  }, [analyzing, s?.export_ready, s?.status])
  const upload = async (file: File) => {
    if (inspecting.current || busy) return false
    inspecting.current = true; setChecking(true); setRejected(''); w.setError('')
    try {
      const inspection = await api.inspect(file)
      if (inspection.purpose !== 'training') onPredictionDataset({file, inspection})
      else await w.upload(file)
      return true
    } catch (e) {
      setRejected(file.name); w.setError(e instanceof Error ? e.message : 'The dataset could not be read.'); return false
    } finally {inspecting.current = false; setChecking(false)}
  }
  const execute = async (approve: boolean, retain = false, reason = '') => {await w.analyze(approve, retain, reason); setStep('')}
  // Flagged observations without a recorded decision are retained with the system's default reason; Review flagged observations stays available.
  const reviewOrRun = (approve: boolean) => {setApproved(approve); void execute(approve, true).catch(() => {})}
  const review = () => {setApproved(false); if (!s?.approved) setStep('confirm'); else setStep('iqr')}
  const run = () => {w.setError(''); if (!s?.approved) setStep('confirm'); else reviewOrRun(false)}
  return <>
    <WorkflowHeading stage="training" current={s?.status === 'complete' ? 3 : s ? 2 : 1}/>
    <div className="workflow-grid">
      <section className="panel workflow-data" aria-labelledby="training-data-title">
        <div className="workflow-card-heading"><span className="heading-icon"><Database size={19}/></span><div><h2 id="training-data-title">Training dataset</h2><p>Six predictors + recorded Actual Waiting Time</p></div><span className="small-badge">01</span></div>
        <DatasetInput w={inputWorkspace} context="training" rejected={rejected} upload={upload} usePrevious={() => {setRejected(''); w.setError('')}}/>
        {w.error && !rejected && <div className="inline-error" role="alert"><p>{friendlyError(w.error)}</p><details className="error-details"><summary>Show error details</summary><p>{w.error}</p></details></div>}
      </section>
      <section className="panel workflow-setup" aria-labelledby="training-setup-title">
        <div className="workflow-card-heading"><span className="heading-icon"><SlidersHorizontal size={19}/></span><div><h2 id="training-setup-title">Model setup</h2><p>Train and evaluate both models</p></div><span className="small-badge">02</span></div>
        <label>Saved training dataset<select aria-label="Saved training dataset" value={s?.id || ''} disabled={busy || !w.experiments.some(item => item.compatible)} onChange={e => void w.select(e.target.value).catch(() => {})}><option value="" disabled>Select a dataset</option>{w.experiments.filter(item => item.compatible).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        {s ? <>
          <div className="split-summary"><div><strong>{s.training.toLocaleString()}</strong><span>Training rows</span></div><div><strong>{s.test.toLocaleString()}</strong><span>Held-out test rows</span></div></div>
          <AnalysisSettings key={s.id} w={inputWorkspace} onReview={review} expanded/>
        </> : <div className="setup-guide"><p>Your dataset supplies the examples both models learn from.</p><ul><li><Check size={15}/>Traditional MLR uses the six predictors.</li><li><Check size={15}/>Enhanced MLR adds your selected interactions.</li><li><Check size={15}/>Both are evaluated on the same held-out rows.</li></ul></div>}
        <div className="run-area">
          {s && !declarationsReady && <p className="setup-notice" id="training-readiness">Complete the recorded-wait and input-availability declarations in Research documentation before training.</p>}
          <button className="button primary run-button" aria-describedby={s && !declarationsReady ? 'training-readiness' : undefined} disabled={busy || !!rejected || !!step || !s || !declarationsReady} onClick={run}>{busy ? <LoaderCircle size={18} className="spinning"/> : <Play size={17}/>} {analyzing ? 'Training models...' : checking ? 'Checking file...' : w.working ? 'Please wait...' : 'Train & evaluate'}{!busy && <ArrowRight size={17}/>}</button>
          <p>Accuracy is measured against recorded waits in the held-out test set.</p>
          {!!s && s.flagged > s.reviewed && <button className="text-button" disabled={busy || !!rejected} onClick={review}>Review {s.flagged - s.reviewed} flagged observations</button>}
        </div>
      </section>
    </div>
    <section ref={resultPanel} className="panel workflow-results" aria-labelledby="training-results-title" aria-busy={analyzing}>
      <div className="workflow-card-heading"><span className="result-section-number">03</span><div><h2 id="training-results-title">Training & validation results</h2><p>Traditional MLR and Enhanced MLR on the same test observations</p></div>{s?.status === 'complete' && <a className="button small" href="#/predict">Use models for predictions<ArrowRight size={15}/></a>}</div>
      {analyzing ? <div className="analysis-loading" role="status"><LoadingBus/><h3>Training your models</h3><p>Fitting both models and evaluating recorded test waits. Results appear here when ready.</p></div>
        : s?.export_ready && s.status !== 'error' ? <AnalysisResults key={`${s.id}:${s.revision}`} s={s}/>
        : <ComparisonEmpty stage="training" error={s?.status === 'error' ? 'The analysis needs attention. Check the message by your dataset and try again.' : undefined}/>}
    </section>
    <SOPSolutions key={`sop:${s?.id}:${s?.revision}`} s={s} busy={busy} onReview={review}/>
    {step === 'confirm' && <ConfirmInteractions w={w} close={() => setStep('')} confirm={() => reviewOrRun(true)}/>}
    {step === 'iqr' && <IQRReview w={w} close={() => setStep('')} proceed={reason => execute(approved, true, reason)}/>}
  </>
}
