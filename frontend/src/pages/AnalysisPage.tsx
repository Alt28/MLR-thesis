import { useEffect, useRef, useState } from 'react'
import { ArrowRight, ChartNoAxesCombined, LoaderCircle, Play } from 'lucide-react'
import type { Workspace } from '../hooks/useExperiment'
import { DatasetInput } from '../components/DatasetInput'
import { AnalysisSettings, ConfirmInteractions } from '../components/AnalysisSettings'
import { IQRReview } from '../components/IQRReview'
import { AnalysisResults } from '../components/AnalysisResults'
import { LoadingBus } from '../components/LoadingBus'
import { friendlyError } from '../services/presentation'

export function AnalysisPage({w}: {w: Workspace}) {
  const s = w.experiment
  const [rejected, setRejected] = useState('')
  const [step, setStep] = useState('')
  const [approved, setApproved] = useState(false)
  const resultPanel = useRef<HTMLElement>(null)
  const wasAnalyzing = useRef(false)
  const analyzing = w.operation === 'analyze' || s?.status === 'running'
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
  const upload = async (file: File) => {setRejected(''); try {await w.upload(file)} catch {setRejected(file.name)}}
  const execute = async (approve: boolean, retain = false, reason = '') => {await w.analyze(approve, retain, reason); setStep('')}
  const reviewOrRun = (approve: boolean) => {setApproved(approve); if (s && s.flagged > s.reviewed) setStep('iqr'); else void execute(approve).catch(() => {})}
  const review = () => {setApproved(false); if (!s?.approved) setStep('confirm'); else setStep('iqr')}
  const run = () => {w.setError(''); if (!s?.approved) setStep('confirm'); else reviewOrRun(false)}
  return <>
    <div className="analysis-title"><span className="eyebrow">TRANSPORTATION ANALYSIS</span><h1>Waiting-time analysis</h1><p>Explore bus and train waiting times, with station conditions explained.</p>
      <ol className="journey-steps" aria-label="Analysis steps">{['Upload Dataset', 'Analyze', 'View Prediction', 'View Station Condition'].map((label, index) => <li key={label}><span>{index + 1}</span>{label}</li>)}</ol>
    </div>
    <div className="analysis-layout">
      <section className="analysis-input panel"><div className="section-title"><span className="section-number">01</span><h2>Transportation Dataset</h2></div>
        <DatasetInput w={w} rejected={rejected} upload={file => void upload(file)} usePrevious={() => {setRejected(''); w.setError('')}}/>
        {w.error && !rejected && <div className="inline-error" role="alert"><p>{friendlyError(w.error)}</p><details className="error-details"><summary>Show error details</summary><p>{w.error}</p></details></div>}
        <div className="run-area">
          <button className="button primary run-button" disabled={!s || w.busy || !!rejected || !!step} onClick={run}>{w.busy ? <LoaderCircle size={18} className="spinning"/> : <Play size={17}/>} {analyzing ? 'Analyzing your dataset…' : w.working ? 'Please wait…' : 'Analyze Dataset'}{!w.busy && <ArrowRight size={17}/>}</button>
          <p>{s ? 'Predict waiting time and view station conditions.' : 'Upload a valid dataset to begin.'}</p>
          {s && s.flagged > s.reviewed && <><p>{s.flagged - s.reviewed} unusual observations require review.</p><button className="text-button" disabled={w.busy || !!rejected} onClick={review}>Review observations</button></>}
        </div>
        {s && <AnalysisSettings key={s.id} w={w} onReview={review}/>}
      </section>
      <section ref={resultPanel} className="analysis-output panel" aria-labelledby="results-title" aria-busy={analyzing}>
        <div className="section-title"><span className="section-number">02</span><h2 id="results-title">Analysis Result</h2></div>
        {analyzing ? <div className="analysis-loading" role="status" aria-live="polite"><LoadingBus/><h3>Analyzing your dataset…</h3><p>Please keep this page open. Your analysis includes:</p><ul><li>Preparing your data</li><li>Running prediction models</li><li>Evaluating the results</li><li>Preparing the station condition</li></ul><small>Results appear automatically when the analysis is complete.</small></div>
          : s?.export_ready && s.status !== 'error' ? <><p className="sr-only" role="status">Your prediction and station condition are ready to view.</p><AnalysisResults key={`${s.id}:${s.revision}`} s={s}/></>
          : <div className="results-empty" role="status"><ChartNoAxesCombined size={36} strokeWidth={1.3}/><h3>{s?.status === 'error' ? 'The analysis needs attention' : s?.classification_stale ? 'Update station classification' : 'Your results will appear here'}</h3><p>{s?.status === 'error' ? 'Check the message beside your dataset, then select Analyze Dataset to try again.' : s?.classification_stale ? 'Select Analyze Dataset to apply the updated classification rules. Your saved data and review decisions are preserved.' : s ? 'Your dataset is ready. Select Analyze Dataset to see the predicted waiting time and station condition.' : 'Start by uploading a CSV or Excel file in Transportation Dataset. Then select Analyze Dataset to see your prediction and station condition.'}</p></div>}
      </section>
    </div>
    {step === 'confirm' && <ConfirmInteractions w={w} close={() => setStep('')} confirm={() => reviewOrRun(true)}/>}
    {step === 'iqr' && <IQRReview w={w} close={() => setStep('')} proceed={reason => execute(approved, true, reason)}/>}
  </>
}
