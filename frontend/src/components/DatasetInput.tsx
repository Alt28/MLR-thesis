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

export function DatasetInput({w, rejected, upload, usePrevious}: {w: Workspace; rejected: string; upload: (file: File) => void; usePrevious: () => void}) {
  const s = w.experiment
  const input = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<Row[]>([])
  const [previewError, setPreviewError] = useState('')
  const [full, setFull] = useState(false)
  useEffect(() => {
    let active = true; setPreview([]); setPreviewError('')
    if (s) api.table(s.id, 'dataset', '', 0, 3).then(data => {if(active) setPreview(data.rows)}).catch(e=>{if(active) setPreviewError(e.message)})
    return () => {active=false}
  }, [s?.id])
  return <div className="dataset-input">
    <div className={`dataset-drop import-area ${s ? 'has-dataset' : ''}`} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault(); if(!w.busy && e.dataTransfer.files[0]) upload(e.dataTransfer.files[0])}}>
      {!s && <div className="import-intro"><Upload size={24} strokeWidth={1.6}/><h3>Choose your dataset</h3><p>Drop a file here or choose an import option.</p></div>}
      <div className="dataset-import-actions">
        <button className="button local-upload-trigger" disabled={w.busy} onClick={()=>input.current?.click()}><Upload size={17}/>{w.operation === 'upload' ? 'Checking file...' : s ? 'Replace Dataset' : 'Upload Dataset'}</button>
        <CloudImport w={w} imported={usePrevious}/>
      </div>
      <div className="import-help"><span>CSV or XLSX · Up to 25 MB</span><details className="template-options"><summary>Templates</summary><div><a href="/api/templates/csv">Download CSV</a><a href="/api/templates/xlsx">Download Excel</a></div></details></div>
    </div>
    <input ref={input} className="sr-only" type="file" accept=".csv,.xlsx" aria-label="Upload transportation dataset" disabled={w.busy} onChange={e=>{const file=e.target.files?.[0]; if(file) upload(file); e.target.value=''}}/>
    {rejected && <div className="inline-error" role="alert"><strong>We couldn't use {rejected}</strong><p>{friendlyError(w.error, 'dataset')}</p>{s && <button className="text-button" onClick={usePrevious}>Use the previous valid dataset</button>}</div>}
    {s && !rejected && <>
      <div className="dataset-file-card">
        <div className="file-summary"><FileSpreadsheet size={23}/><div><strong title={s.name}>{s.name}</strong><span>{s.records.toLocaleString()} observations</span></div></div>
        <div className="dataset-validation"><span className="validation-status"><CheckCircle2 size={14}/> Format valid</span><span className="validation-note">7/7 required variables detected</span></div>
        <DatasetTransport s={s} w={w}/>
        {s.provenance && s.provenance.status !== 'recorded_declared' && <details className="dataset-source-note"><summary>{s.provenance.status === 'prototype' ? 'Prototype data — testing only' : 'Data source not documented'}</summary><p>See Research documentation in Advanced Settings.{s.provenance.status === 'prototype' && ' These observations are for software testing, not final research evidence.'}</p></details>}
      </div>
      <div className="preview-heading"><h3>Dataset preview</h3><button className="text-button" onClick={()=>setFull(true)}>View Full Dataset</button></div>
      {previewError ? <p className="inline-error" role="alert">{previewError}</p> : preview.length ? <div className="table-scroll preview-table" tabIndex={0} aria-label="Dataset preview, scroll to view all variables"><table><thead><tr>{[...PREDICTORS,TARGET].map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{preview.map((row,i)=><tr key={i}>{[...PREDICTORS,TARGET].map(c=><td key={c}>{format(row[c])}</td>)}</tr>)}</tbody></table></div> : <p role="status">Loading preview…</p>}<p className="small-text muted">First 3 observations · Scroll to see all columns</p>
    </>}
    <details className="disclosure required-variables"><summary>Required variables</summary><div className="disclosure-body"><ul>{[...PREDICTORS,TARGET].map(c=><li key={c}>{c}{c===TARGET ? ' (minutes)' : ''}</li>)}</ul><p>Only these six predictors enter the models. Extra columns are kept as metadata. Add Station ID (or Station) to summarize held-out scores by station.</p></div></details>
    {full && s && <Modal title="Dataset preview" close={()=>setFull(false)}><div className="modal-body"><DataTable s={s} name="dataset"/></div></Modal>}
  </div>
}
