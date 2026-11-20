import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ChartNoAxesCombined, LoaderCircle, Play } from 'lucide-react'
import type { Workspace } from '../hooks/useExperiment'
import { DatasetInput } from '../components/DatasetInput'
import { AnalysisSettings, ConfirmInteractions } from '../components/AnalysisSettings'
import { IQRReview } from '../components/IQRReview'
import { AnalysisResults } from '../components/AnalysisResults'
import { LoadingBus } from '../components/LoadingBus'
import { friendlyError } from '../services/presentation'
import { api } from '../services/api'
import { PredictionResults } from '../components/PredictionOnly'
import type { PredictionDataset } from '../components/PredictionOnly'
import type { PredictionOutput } from '../types'
import { SOPSolutions } from '../components/SOPSolutions'

export function AnalysisPage({w}: {w: Workspace}) {
  const s = w.experiment
  const [rejected, setRejected] = useState('')
  const [step, setStep] = useState('')
  const [approved, setApproved] = useState(false)
  const [predictionDataset, setPredictionDataset] = useState<PredictionDataset | null>(null)
  const [predictionResult, setPredictionResult] = useState<PredictionOutput | null>(null)
  const [predicting, setPredicting] = useState(false)
  const [checking, setChecking] = useState(false)
  const inspecting = useRef(false)
  const predictionRequest = useRef(0)
  const busy = w.busy || checking || predicting
  const inputWorkspace = {...w, busy, operation: checking ? 'upload' as const : w.operation}
  const resultPanel = useRef<HTMLElement>(null)
  const wasAnalyzing = useRef(false)
  const analyzing = predicting || w.operation === 'analyze' || s?.status === 'running'
  const modelReady = s?.status === 'complete' && !s.classification_stale
  useEffect(() => {predictionRequest.current++; setPredictionResult(null)}, [s?.id, s?.revision])
  useEffect(() => {setApproved(false); setStep('')}, [s?.id])
  useEffect(() => {
    if (wasAnalyzing.current && !analyzing && s?.export_ready && s.status === 'complete') {
      const panel = resultPanel.current
      if (panel && !panel.closest('[hidden]') && panel.getBoundingClientRect().top > innerHeight * .7) {
        panel.scrollIntoView({block: 'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'})
      }
    }
    wasAnalyzing.current = analyzing
  }, [analyzing, s?.export_ready, s?.status])
  const upload = async (file: File) => {
    if (inspecting.current || busy) return
    inspecting.current = true; setChecking(true); setRejected(''); w.setError('')
    predictionRequest.current++; setPredictionResult(null)
    try {
      const inspection = await api.inspect(file)
      if (inspection.purpose === 'prediction') {
        setPredictionDataset({file, inspection})
        if (!modelReady) {
          const trained = w.experiments.find(item => item.status === 'complete')
          if (trained && trained.id !== s?.id) await w.select(trained.id)
        }
      } else {
        await w.upload(file); setPredictionDataset(null)
      }
    } catch (e) {
      setRejected(file.name); w.setError(e instanceof Error ? e.message : 'The dataset could not be read.')
    } finally {inspecting.current = false; setChecking(false)}
  }
  const showTraining = () => {predictionRequest.current++; setPredictionDataset(null); setPredictionResult(null); setRejected(''); w.setError('')}
  const predict = async () => {
    if (!s || !predictionDataset || !modelReady || busy) return
    const request = ++predictionRequest.current
    setPredicting(true); setPredictionResult(null); w.setError('')
    try {
      const result = await api.predict(s, predictionDataset.file)
      if (request === predictionRequest.current) setPredictionResult(result)
    } catch (e) {if (request === predictionRequest.current) w.setError(e instanceof Error ? e.message : 'Prediction failed.')}
    finally {setPredicting(false)}
  }
  const execute = async (approve: boolean, retain = false, reason = '') => {await w.analyze(approve, retain, reason); setStep('')}
  const reviewOrRun = (approve: boolean) => {setApproved(approve); if (s && s.flagged > s.reviewed) setStep('iqr'); else void execute(approve).catch(() => {})}
  const review = () => {setApproved(false); if (!s?.approved) setStep('confirm'); else setStep('iqr')}
  const run = () => {w.setError(''); if (predictionDataset) void predict(); else if (!s?.approved) setStep('confirm'); else reviewOrRun(false)}
  return <>
    <div className="analysis-title"><span className="eyebrow">TRANSPORTATION ANALYSIS</span><h1>Waiting-time analysis</h1><p>Explore bus and train waiting times, with station conditions explained.</p>
      <ol className="journey-steps" aria-label="Analysis steps">{['Upload Dataset', 'Analyze', 'View Prediction', 'View Station Condition'].map((label, index) => <li key={label}><span>{index + 1}</span><strong>{label}</strong></li>)}</ol>
    </div>
    <div className="analysis-layout">
      <section className="analysis-input panel"><div className="section-title"><span className="section-number">01</span><h2>Transportation Dataset</h2></div>
        <DatasetInput w={inputWorkspace} predictionDataset={predictionDataset} rejected={rejected} upload={file => void upload(file)} imported={showTraining} usePrevious={() => {setRejected(''); w.setError('')}}/>
        {w.error && !rejected && <div className="inline-error" role="alert"><p>{friendlyError(w.error)}</p><details className="error-details"><summary>Show error details</summary><p>{w.error}</p></details></div>}
        <div className="run-area">
          <button className="button primary run-button" disabled={busy || !!rejected || !!step || (predictionDataset ? !modelReady : !s)} onClick={run}>{busy ? <LoaderCircle size={18} className="spinning"/> : <Play size={17}/>} {analyzing ? 'Analyzing your dataset…' : checking ? 'Checking file...' : w.working ? 'Please wait…' : 'Analyze Dataset'}{!busy && <ArrowRight size={17}/>}</button>
          <p>{predictionDataset ? 'Compare Traditional and Enhanced MLR predictions for your uploaded rows.' : s ? 'Train both models and measure accuracy against recorded waits.' : 'Upload a dataset to begin. Actual Waiting Time may be blank.'}</p>
          {predictionDataset && !modelReady && <p className="decision-note" role="status">Your dataset is accepted. Trained models are needed to calculate predictions. Select a trained model below, or upload a separate dataset with recorded waits to train both models first.</p>}
          {!predictionDataset && s && s.flagged > s.reviewed && <><p>{s.flagged - s.reviewed} unusual observations require review.</p><button className="text-button" disabled={busy || !!rejected} onClick={review}>Review observations</button></>}
        </div>
        {predictionDataset ? <details className="disclosure prediction-model"><summary>Model used for predictions</summary><div className="disclosure-body">
          <label>Saved model dataset<select aria-label="Saved model dataset" value={s?.id || ''} disabled={busy || !w.experiments.length} onChange={event => void w.select(event.target.value).catch(() => {})}>
            {!s && <option value="">No model available</option>}
            {w.experiments.map(item => <option key={item.id} value={item.id}>{item.name} — {(item.id === s?.id ? s.status : item.status) === 'complete' ? 'Trained' : 'Needs analysis'}</option>)}
          </select></label>
          {s && <><p className="section-caption">Revision {s.revision}. Use the same units and category definitions as this model's training data.</p><button className="text-button" disabled={busy} onClick={showTraining}>View saved model analysis</button></>}
          {s?.provenance && <details className="dataset-source-note"><summary>Model training source notes</summary><p>{s.provenance.message}</p></details>}
        </div></details> : s && <AnalysisSettings key={s.id} w={inputWorkspace} onReview={review}/>}
      </section>
      <section ref={resultPanel} className="analysis-output panel" aria-labelledby="results-title" aria-busy={analyzing}>
        <div className="section-title"><span className="section-number">02</span><h2 id="results-title">Analysis Result</h2></div>
        {analyzing ? <div className="analysis-loading" role="status" aria-live="polite"><LoadingBus/><h3>Analyzing your dataset…</h3><p>Please keep this page open. Your analysis includes:</p><ul><li>Preparing your data</li><li>Running prediction models</li>{!predictionDataset && <li>Evaluating the results</li>}<li>Preparing the station condition</li></ul><small>Results appear automatically when the analysis is complete.</small></div>
          : predictionDataset ? predictionResult && s && !rejected ? <PredictionResults key={`${predictionResult.experiment_id}:${predictionResult.model_revision}`} s={s} result={predictionResult}/> : <div className="results-empty" role="status"><ChartNoAxesCombined size={36} strokeWidth={1.3}/><h3>Your results will appear here</h3><p>{rejected ? 'Check the upload message or use the previous valid dataset.' : modelReady ? 'Select Analyze Dataset to see Traditional and Enhanced MLR predictions side by side. Actual Waiting Time will remain blank.' : 'Your uploaded rows are accepted. Both models need to be trained before they can estimate waiting times.'}</p></div>
          : s?.export_ready && s.status !== 'error' ? <><p className="sr-only" role="status">Your prediction and station condition are ready to view.</p><AnalysisResults key={`${s.id}:${s.revision}`} s={s}/></>
          : <div className="results-empty" role="status"><ChartNoAxesCombined size={36} strokeWidth={1.3}/><h3>{s?.status === 'error' ? 'The analysis needs attention' : s?.classification_stale ? 'Update station classification' : 'Your results will appear here'}</h3><p>{s?.status === 'error' ? 'Check the message beside your dataset, then select Analyze Dataset to try again.' : s?.classification_stale ? 'Select Analyze Dataset to apply the updated classification rules. Your saved data and review decisions are preserved.' : s ? 'Your dataset is ready. Select Analyze Dataset to see the predicted waiting time and station condition.' : 'Start by uploading a CSV or Excel file in Transportation Dataset. Then select Analyze Dataset to see your prediction and station condition.'}</p></div>}
      </section>
    </div>
    <SOPSolutions key={`sop:${s?.id}:${s?.revision}`} s={s} busy={busy} onReview={() => {showTraining(); review()}}/>
    {step === 'confirm' && <ConfirmInteractions w={w} close={() => setStep('')} confirm={() => reviewOrRun(true)}/>}
    {step === 'iqr' && <IQRReview w={w} close={() => setStep('')} proceed={reason => execute(approved, true, reason)}/>}
  </>
}
