import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, FileSpreadsheet, Upload } from 'lucide-react'
import type { Workspace } from '../hooks/useExperiment'
import type { Row } from '../types'
import { PREDICTORS, TARGET } from '../types'
import { api } from '../services/api'
import { friendlyError } from '../services/presentation'
import { DataTable } from './DataTable'
import { DatasetTransport } from './TransportOutputs'
import { CloudImport } from './CloudImport'
import { Modal, format } from './Common'
import type { PredictionDataset } from './PredictionOnly'

export function DatasetInput({w, context = 'training', predictionDataset = null, rejected, upload, usePrevious}: {w: Workspace; context?: 'training' | 'prediction'; predictionDataset?: PredictionDataset | null; rejected: string; upload: (file: File) => Promise<boolean>; usePrevious: () => void}) {
  const sourceReview = predictionDataset?.inspection.purpose === 'source_review'
  const s = w.experiment
  const hasDataset = !!s || !!predictionDataset
  const input = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<Row[]>([])
  const [previewError, setPreviewError] = useState('')
  const [full, setFull] = useState(false)
  useEffect(() => {
    let active = true; setPreview([]); setPreviewError('')
    if (s && !predictionDataset) api.table(s.id, 'dataset', '', 0, 6).then(data => {if(active) setPreview(data.rows)}).catch(e=>{if(active) setPreviewError(e.message)})
    return () => {active=false}
  }, [s?.id, predictionDataset])
  return <div className="dataset-input">
    <div className={`dataset-drop import-area ${hasDataset ? 'has-dataset' : ''}`} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault(); if(!w.busy && e.dataTransfer.files[0]) upload(e.dataTransfer.files[0])}}>
      {!hasDataset && <div className="import-intro"><span className="upload-icon"><Upload size={25} strokeWidth={1.6}/></span><h3>Drop your {context === 'training' ? 'training dataset' : 'new observations'} here</h3><p>Choose a CSV or Excel file, or browse your dataset library.</p></div>}
      <div className="dataset-import-actions">
        <button className="button local-upload-trigger" disabled={w.busy} onClick={()=>input.current?.click()}><Upload size={17}/>{w.operation === 'upload' ? 'Checking file...' : hasDataset ? 'Replace Dataset' : 'Upload Dataset'}</button>
        <CloudImport w={w} upload={upload}/>
      </div>
      <div className="import-help"><span>CSV or XLSX · Up to 25 MB</span><details className="template-options"><summary>Templates</summary><div><a href="/api/templates/csv">Download CSV</a><a href="/api/templates/xlsx">Download Excel</a></div></details></div>
    </div>
    <input ref={input} className="sr-only" type="file" accept=".csv,.xlsx" aria-label="Upload transportation dataset" disabled={w.busy} onChange={e=>{const file=e.target.files?.[0]; if(file) upload(file); e.target.value=''}}/>
    {rejected && <div className="inline-error" role="alert"><strong>We couldn't use {rejected}</strong><p>{friendlyError(w.error, 'dataset')}</p>{hasDataset && <button className="text-button" onClick={usePrevious}>Use the previous valid dataset</button>}</div>}
    {predictionDataset && !rejected && <div className="dataset-file-card" role="status">
      <div className="file-summary"><FileSpreadsheet size={23}/><div><strong title={predictionDataset.file.name}>{predictionDataset.file.name}</strong><span>{predictionDataset.inspection.rows.toLocaleString()} observations</span></div></div>
      <div className="dataset-validation"><span className="validation-status"><CheckCircle2 size={14}/>{sourceReview ? "Imported for source review" : "Format valid"}</span><span className="validation-note">{sourceReview ? `${6 - Object.keys(predictionDataset.inspection.missing_predictors).length}/6 predictors complete` : "6/6 predictors detected"}</span></div>
      {sourceReview && <div className="decision-note" role="status">{Object.entries(predictionDataset.inspection.missing_predictors).map(([name, count]) => <p key={name}>{name} is missing in {count.toLocaleString()} rows. These rows can be reviewed, but cannot train a model or produce predictions.</p>)}</div>}
      <p className="section-caption">Actual Waiting Time is blank. Predictions require a compatible trained model; accuracy cannot be measured for these rows.</p>
    </div>}
    {predictionDataset && !rejected && <><div className="preview-heading"><h3>Dataset preview</h3></div><div className="table-scroll preview-table" tabIndex={0} aria-label="Prediction dataset preview"><table><thead><tr>{PREDICTORS.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{predictionDataset.inspection.preview.slice(0,3).map((row,i)=><tr key={i}>{PREDICTORS.map(c=><td key={c}>{format(row[c])}</td>)}</tr>)}</tbody></table></div><p className="section-caption">First {Math.min(3, predictionDataset.inspection.preview.length)} rows. Open the source audit below for more observations.</p><details className="disclosure"><summary>Observation timing and source definitions</summary><div className="disclosure-body">{[...predictionDataset.inspection.source_notes, ...predictionDataset.inspection.warnings].map(note=><p key={note}>{note}</p>)}</div></details></>}
    {predictionDataset && !rejected && <details className="disclosure"><summary>View source audit and observation identifiers</summary><div className="disclosure-body"><div className="table-scroll" tabIndex={0} aria-label="Source audit preview"><table><thead><tr>{predictionDataset.inspection.columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{predictionDataset.inspection.preview.map((row,i)=><tr key={i}>{predictionDataset.inspection.columns.map(c=><td key={c}>{format(row[c])}</td>)}</tr>)}</tbody></table></div><p>First {predictionDataset.inspection.preview.length} source records. The imported file retains all rows and audit columns.</p></div></details>}
    {s && !predictionDataset && !rejected && <>
      <div className="dataset-file-card">
        <div className="file-summary"><FileSpreadsheet size={23}/><div><strong title={s.name}>{s.name}</strong><span>{s.records.toLocaleString()} observations</span></div></div>
        <div className="dataset-validation"><span className="validation-status"><CheckCircle2 size={14}/> Format valid</span><span className="validation-note">6 predictors + recorded waiting time</span></div>
        <DatasetTransport s={s} w={w}/>
        {s.provenance && s.provenance.status !== 'recorded_declared' && <details className="dataset-source-note"><summary>Dataset source notes</summary><p>{s.provenance.message}</p><p>See Research documentation in Model settings for the source details.</p></details>}
      </div>
      <div className="preview-heading"><h3>Dataset preview</h3><button className="text-button" onClick={()=>setFull(true)}>View Full Dataset</button></div>
      {previewError ? <p className="inline-error" role="alert">{previewError}</p> : preview.length ? <div className="table-scroll preview-table" tabIndex={0} aria-label="Dataset preview, scroll to view all variables"><table><thead><tr>{[...PREDICTORS,TARGET].map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{preview.map((row,i)=><tr key={i}>{[...PREDICTORS,TARGET].map(c=><td key={c}>{format(row[c])}</td>)}</tr>)}</tbody></table></div> : <p role="status">Loading preview…</p>}<p className="small-text muted">First {preview.length} observations · Scroll to see all columns</p>
    </>}
    <details className="disclosure required-variables"><summary>Required variables</summary><div className="disclosure-body"><ul>{PREDICTORS.map(c=><li key={c}>{c}</li>)}</ul><p><strong>{TARGET} (minutes)</strong> is the target. It is required to train and measure accuracy. Leave it blank or omit the column when predicting new observations with trained models.</p><p>Extra columns and source observation IDs are kept as metadata. Station / Stop is categorical and is used for station summaries. Passenger Volume is a recorded count; Vehicle Frequency is actual recorded operations per hour. Calendar categories must use the documented names.</p></div></details>
    {full && s && <Modal title="Dataset preview" close={()=>setFull(false)}><div className="modal-body"><DataTable s={s} name="dataset"/></div></Modal>}
  </div>
}
