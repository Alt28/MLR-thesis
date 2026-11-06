import { useState } from 'react'
import type { Workspace } from '../hooks/useExperiment'
import { DataTable } from './DataTable'
import { Modal } from './Common'
import { ReviewDialog } from './ResearchForms'

export function IQRReview({w, close, proceed}: {w: Workspace; close: () => void; proceed: (reason: string) => Promise<void>}) {
  const s = w.experiment!
  const [selected, setSelected] = useState<string | null>(null)
  const [reason, setReason] = useState('')
  const remaining = s.flagged - s.reviewed
  return <><Modal canClose={!w.busy} title="Review unusual observations" close={()=>{if(!w.busy) close()}} className="wide-modal"><div className="modal-body"><p><strong>{s.flagged} unusual observations</strong> · {remaining} awaiting a recorded decision.</p><p className="muted">Retain is the default. A flag can represent a valid unusual transportation condition. Review a row to retain, exclude, or correct it.</p><DataTable s={s} name="flags" columns={['Record ID','Factor','Value','Action','Reason']} onRow={w.busy ? undefined : row=>setSelected(String(row['Record ID']))} actionLabel="Review"/>
    {remaining > 0 && <label className="retain-reason">Reason for retaining the remaining {remaining} observations<textarea required rows={2} value={reason} onChange={e=>setReason(e.target.value)} placeholder="Explain why these observations should remain in the training data." maxLength={2000}/><small>Continue Analysis records this reason for each remaining observation. Existing corrections and exclusions are preserved.</small></label>}
    {w.error && <p className="inline-error" role="alert">{w.error}</p>}</div><div className="modal-footer"><button className="button" disabled={w.busy} onClick={close}>Back</button><button className="button primary" disabled={w.busy || (remaining > 0 && !reason.trim())} onClick={()=>void proceed(reason).catch(()=>{})}>Continue Analysis</button></div></Modal>
    {selected && <ReviewDialog id={selected} s={s} w={w} close={()=>setSelected(null)}/>}</>
}
