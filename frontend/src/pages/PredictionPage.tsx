import { useEffect, useRef, useState } from 'react'
import { ArrowRight, Database, GitBranch, LoaderCircle, Play } from 'lucide-react'
import type { Workspace } from '../hooks/useExperiment'
import { DatasetInput } from '../components/DatasetInput'
import { PredictionResults } from '../components/PredictionOnly'
import { LoadingBus } from '../components/LoadingBus'
import type { PredictionDataset } from '../components/PredictionOnly'
import { ComparisonEmpty, WorkflowHeading } from '../components/WorkflowUI'
import { api } from '../services/api'
import { SCHEMA_VERSION } from '../types'
import type { Experiment, PredictionOutput } from '../types'

export function PredictionPage({w, incoming, consumeIncoming}: {w: Workspace; incoming: PredictionDataset | null; consumeIncoming: () => void}) {
  const [dataset, setDataset] = useState<PredictionDataset | null>(null)
  const [result, setResult] = useState<PredictionOutput | null>(null)
  const [mode, setMode] = useState('unknown')
  const [modelId, setModelId] = useState('')
  const [model, setModel] = useState<Experiment | null>(null)
  const [loadingModel, setLoadingModel] = useState(false)
  const [inputsAvailable, setInputsAvailable] = useState(false)
  const [checking, setChecking] = useState(false)
  const [predicting, setPredicting] = useState(false)
  const [error, setError] = useState('')
  const [rejected, setRejected] = useState('')
  const [wrongPage, setWrongPage] = useState(false)
  const inspecting = useRef(false)
  const request = useRef(0)
  const resultPanel = useRef<HTMLElement>(null)
  const busy = w.busy || checking || predicting || loadingModel
  const sourceReview = dataset?.inspection.purpose === 'source_review'
  const candidates = w.experiments.filter(item => item.compatible && item.status === 'complete' && (mode === 'unknown' || item.transport_mode === mode))
  const selected = candidates.find(item => item.id === modelId)
  const modelReady = !sourceReview && !!selected && model?.id === selected.id && model.revision === selected.revision && model.status === 'complete' && model.schema_version === SCHEMA_VERSION && model.transport_mode === mode
  const modeName = mode === 'train' ? 'Train' : 'Bus'
  const blockReason = sourceReview ? 'Complete the missing predictors shown in the dataset review before generating predictions.'
    : !dataset ? 'Upload a dataset with the six predictors to begin.'
    : mode === 'unknown' ? 'Select Bus or Train for this dataset.'
    : !candidates.length ? `No trained ${modeName} model is available for these six predictors. Go to Training and train both models using recorded waiting times first.`
    : !modelReady ? 'Choose a compatible trained model to continue.'
    : !inputsAvailable ? 'Confirm that the passenger and vehicle counts were available at prediction time.' : ''
  const acceptDataset = (value: PredictionDataset) => {
    request.current++; setDataset(value); setMode(value.inspection.transport_mode); setInputsAvailable(false)
    setResult(null); setError(''); setRejected(''); setWrongPage(false)
  }
  useEffect(() => {
    if (incoming) {acceptDataset(incoming); consumeIncoming()}
  }, [incoming, consumeIncoming])
  useEffect(() => {
    if (!candidates.some(item => item.id === modelId)) setModelId(candidates[0]?.id || '')
  }, [w.experiments, mode, modelId])
  useEffect(() => {
    let active = true
    request.current++; setResult(null); setModel(null)
    if (!selected) {setLoadingModel(false); return}
    setLoadingModel(true); setError('')
    api.get(selected.id).then(value => {if (active) setModel(value)})
      .catch(e => {if (active) setError(e.message)})
      .finally(() => {if (active) setLoadingModel(false)})
    return () => {active = false}
  }, [selected?.id, selected?.revision, selected?.status])
  useEffect(() => {
    if (result && resultPanel.current && !resultPanel.current.closest('[hidden]')) resultPanel.current.scrollIntoView({block:'start', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'})
  }, [result])
  const upload = async (file: File) => {
    if (inspecting.current || busy) return false
    inspecting.current = true; setChecking(true); setError(''); setRejected(''); setWrongPage(false)
    request.current++; setResult(null)
    try {
      const inspection = await api.inspect(file)
      if (inspection.purpose === 'training') {
        setWrongPage(true)
        throw new Error('This file contains recorded Actual Waiting Time values. Use the Training page to train models and compare accuracy. This page predicts rows with blank or omitted actual waiting times.')
      }
      acceptDataset({file, inspection}); return true
    } catch (e) {setRejected(file.name); setError(e instanceof Error ? e.message : 'The dataset could not be read.'); return false}
    finally {inspecting.current = false; setChecking(false)}
  }
  const predict = async () => {
    if (!model || !dataset || !modelReady || !inputsAvailable || busy || rejected) return
    const current = ++request.current
    setPredicting(true); setResult(null); setError('')
    try {
      const value = await api.predict(model, dataset.file, mode, inputsAvailable)
      if (request.current === current) setResult(value)
    } catch (e) {if (request.current === current) setError(e instanceof Error ? e.message : 'Prediction failed.')}
    finally {setPredicting(false)}
  }
  // Prediction selection and errors never replace the training workspace's dataset.
  const inputWorkspace = {...w, experiment: null, busy, error, setError, operation: checking ? 'upload' as const : null}
  return <>
    <WorkflowHeading stage="prediction" current={result ? 3 : dataset ? 2 : 1}/>
    <div className="prediction-explainer"><GitBranch size={19}/><p><strong>Predict first. Evaluate when actual waits are recorded.</strong> This page compares the two models' estimates. Accuracy scores belong to the recorded test data on Training.</p></div>
    <div className="workflow-grid">
      <section className="panel workflow-data" aria-labelledby="prediction-data-title">
        <div className="workflow-card-heading"><span className="heading-icon"><Database size={19}/></span><div><h2 id="prediction-data-title">New observations</h2><p>Leave Actual Waiting Time blank or omit its column</p></div><span className="small-badge">01</span></div>
        <DatasetInput w={inputWorkspace} context="prediction" predictionDataset={dataset} rejected={rejected} upload={upload} usePrevious={() => {setRejected(''); setError(''); setWrongPage(false)}}/>
        {wrongPage && <a className="button small" href="#/training">Go to Training<ArrowRight size={15}/></a>}
        {error && !rejected && <p className="inline-error" role="alert">{error}</p>}
      </section>
      <section className="panel workflow-setup" aria-labelledby="prediction-model-title">
        <div className="workflow-card-heading"><span className="heading-icon"><GitBranch size={19}/></span><div><h2 id="prediction-model-title">Trained models</h2><p>Use the matching bus or train models</p></div><span className="small-badge">02</span></div>
        <label>Transport mode<select aria-label="Prediction dataset mode" value={mode} disabled={busy || (!!dataset && dataset.inspection.transport_mode !== 'unknown')} onChange={e => {request.current++; setMode(e.target.value); setResult(null); setInputsAvailable(false)}}><option value="unknown">Select Bus or Train</option><option value="bus">Bus</option><option value="train">Train</option></select></label>
        <label className="model-select-label">Saved training run<select aria-label="Saved model dataset" value={selected?.id || ''} disabled={busy || !candidates.length} onChange={e => setModelId(e.target.value)}><option value="" disabled>{candidates.length ? 'Choose a trained model' : 'No compatible trained models'}</option>{candidates.map(item => <option key={item.id} value={item.id}>{item.name} — Revision {item.revision}</option>)}</select></label>
        {model && selected && <div className="selected-model-card"><span className="model-ready-dot"/><div><strong>Traditional + Enhanced MLR</strong><p>{model.transport_mode === 'train' ? 'Train' : 'Bus'} models · Revision {model.revision}</p><small>Use the same units, stations and category definitions as the training data.</small></div></div>}
        {dataset && !sourceReview && <label className="checkbox-line prediction-consent"><input type="checkbox" aria-label="Confirm prediction input availability" checked={inputsAvailable} disabled={busy} onChange={e => {setInputsAvailable(e.target.checked); setResult(null)}}/><span>These passenger and vehicle counts were available at prediction time, from completed observation windows.</span></label>}
        {blockReason && <div id="model-block-reason" className="setup-notice" role="status"><p>{blockReason}</p>{dataset && !sourceReview && mode !== 'unknown' && !candidates.length && <a href="#/training">Go to Training<ArrowRight size={14}/></a>}</div>}
        <div className="run-area"><button className="button primary run-button" disabled={busy || !!rejected || !!blockReason} aria-describedby={blockReason ? 'model-block-reason' : undefined} onClick={() => void predict()}>{busy ? <LoaderCircle size={18} className="spinning"/> : <Play size={17}/>} {predicting ? 'Generating predictions...' : checking ? 'Checking file...' : loadingModel ? 'Loading models...' : 'Generate predictions'}{!busy && <ArrowRight size={17}/>}</button><p>Predicted times appear in their own columns. Actual Waiting Time stays blank.</p></div>
        {model?.provenance && <details className="disclosure model-source"><summary>Training source notes</summary><div className="disclosure-body"><p>{model.provenance.message}</p></div></details>}
      </section>
    </div>
    <section ref={resultPanel} className="panel workflow-results" aria-labelledby="prediction-results-title" aria-busy={predicting}>
      <div className="workflow-card-heading"><span className="result-section-number">03</span><div><h2 id="prediction-results-title">Prediction comparison</h2><p>Two model estimates for each new observation, in minutes</p></div>{result && <span className="small-badge success">{result.rows.length.toLocaleString()} rows</span>}</div>
      {predicting ? <div className="analysis-loading" role="status"><LoadingBus/><h3>Generating both predictions</h3><p>Your trained models are processing the uploaded observations. Results appear here when ready.</p></div> : (checking || loadingModel) && !result ? <div className="analysis-loading" role="status"><LoadingBus/><h3>{checking ? 'Reading your dataset' : 'Loading the trained models'}</h3><p>{checking ? 'Checking the six predictors in the uploaded file.' : 'Preparing the saved Traditional and Enhanced MLR models.'}</p></div> : result && model && !rejected ? <PredictionResults key={`${result.experiment_id}:${result.model_revision}`} s={model} result={result}/> : <ComparisonEmpty stage="prediction"/>}
    </section>
  </>
}
