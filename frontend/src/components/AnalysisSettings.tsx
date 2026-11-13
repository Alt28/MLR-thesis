import { useState } from 'react'
import { Plus } from 'lucide-react'
import type { Workspace } from '../hooks/useExperiment'
import { PREDICTORS } from '../types'
import { friendlyError } from '../services/presentation'
import { Modal } from './Common'
import { ResearchDocumentation } from './ResearchProtocol'
import { SeveritySettings, SplitSettings } from './ResearchForms'

const suggestions = [
  ['Passenger Volume','Vehicle Frequency'], ['Passenger Volume','Time of Day'],
  ['Traffic Condition','Time of Day'], ['Weather Condition','Traffic Condition'],
  ['Route Distance','Traffic Condition'], ['Vehicle Frequency','Time of Day'],
  ['Passenger Volume','Vehicle Frequency','Time of Day'],
]
const key = (term: string[]) => [...term].sort().join('|')
export function AnalysisSettings({w, onReview}: {w: Workspace; onReview: () => void}) {
  const s = w.experiment!
  const [modal, setModal] = useState('')
  const terms = [...s.config.pairwise_interactions,...s.config.higher_order_interactions]
  const unresolved = !s.config.vehicle_frequency_unit.trim() || !s.config.route_distance_unit.trim() || s.thresholds.some(row=>row.Status !== 'Valid') || s.evidence.some(row=>row.Status !== 'Valid')
  return <div className="analysis-settings"><details className="disclosure"><summary>Advanced Settings</summary><div className="disclosure-body"><p className="settings-note">{terms.length} interaction terms · {s.approved ? 'Researcher approved' : 'Approval required before running'}</p><h4>Selected interactions</h4>{terms.length ? <ul className="selected-terms">{terms.map(t=><li key={key(t)}>{t.join(' × ')}</li>)}</ul> : <p>No interaction terms selected. Both models will use main effects only.</p>}<div className="settings-actions"><button className="button small" disabled={w.busy} onClick={()=>setModal('documentation')}>Research documentation</button><button className="button small" disabled={w.busy} onClick={()=>setModal('interactions')}>Edit interaction terms</button><button className="button small" disabled={w.busy} onClick={()=>setModal('split')}>Split & IQR settings</button><button className="button small" disabled={w.busy} onClick={()=>setModal('classification')}>Classification definitions</button>{s.reviewed>0 && <button className="button small" disabled={w.busy} onClick={onReview}>Review recorded decisions</button>}</div><p className="settings-note">Changing settings clears the current results. Analyze Dataset again after saving.</p>
    {unresolved && <p className="decision-note"><strong>Classification: Requires Researcher Decision</strong><span>Review unavailable rules, insufficient variation, and measurement units. Training-derived category scores are used unless explicitly overridden.</span><button className="text-button" disabled={w.busy} onClick={()=>setModal('classification')}>Define classification rules</button></p>}
    </div></details>
    {modal==='documentation' && <ResearchDocumentation s={s} w={w} close={()=>setModal('')}/>}
    {modal==='split' && <SplitSettings s={s} w={w} close={()=>{if(!w.busy)setModal('')}}/>}
    {modal==='interactions' && <InteractionSettings w={w} close={()=>setModal('')}/>}
    {modal==='classification' && <Modal canClose={!w.busy} title="Classification definitions" className="wide-modal" close={()=>{if(!w.busy)setModal('')}}><div className="modal-body"><SeveritySettings s={s} w={w} onSaved={()=>setModal('')}/></div></Modal>}
  </div>
}

function InteractionSettings({w,close}: {w: Workspace; close: ()=>void}) {
  const s=w.experiment!
  const [terms,setTerms]=useState([...s.config.pairwise_interactions,...s.config.higher_order_interactions])
  const [options,setOptions]=useState(()=>[...new Map([...suggestions,...terms].map(t=>[key(t),t])).values()])
  const [custom,setCustom]=useState<string[]>([])
  const toggle=(term:string[])=>setTerms(terms.some(t=>key(t)===key(term)) ? terms.filter(t=>key(t)!==key(term)) : [...terms,term])
  return <Modal canClose={!w.busy} title="Approved interaction terms" close={()=>{if(!w.busy)close()}}><form onSubmit={e=>{e.preventDefault();void w.configure({...s.config,pairwise_interactions:terms.filter(t=>t.length===2),higher_order_interactions:terms.filter(t=>t.length>2)},true).then(close).catch(()=>{})}}><div className="modal-body"><p className="muted">Select only interactions supported by your research. All original predictors remain as main effects.</p>{[2,3].map(size=><fieldset key={size}><legend>{size===2?'Pairwise interactions':'Higher-order interactions'}</legend>{options.filter(t=>size===2?t.length===2:t.length>2).map(t=><label className="checkbox-line" key={key(t)}><input type="checkbox" checked={terms.some(term=>key(term)===key(t))} onChange={()=>toggle(t)} disabled={w.busy}/>{t.join(' × ')}</label>)}</fieldset>)}<details className="disclosure"><summary>Add another researcher-defined interaction</summary><div className="disclosure-body">{PREDICTORS.map(f=><label className="checkbox-line" key={f}><input type="checkbox" checked={custom.includes(f)} onChange={e=>setCustom(e.target.checked?[...custom,f]:custom.filter(x=>x!==f))}/>{f}</label>)}<button className="button small" type="button" disabled={custom.length<2 || options.some(t=>key(t)===key(custom))} onClick={()=>{setOptions([...options,custom]);setTerms([...terms,custom]);setCustom([])}}><Plus size={14}/>Add selected combination</button></div></details>{w.error && <p className="inline-error" role="alert">{w.error}</p>}</div><div className="modal-footer"><button type="button" className="button" disabled={w.busy} onClick={close}>Cancel</button><button className="button primary" disabled={w.busy}>Approve selected interactions</button></div></form></Modal>
}

export function ConfirmInteractions({w,close,confirm}: {w:Workspace;close:()=>void;confirm:()=>void}) {
  const [approved,setApproved]=useState(false)
  const terms=[...w.experiment!.config.pairwise_interactions,...w.experiment!.config.higher_order_interactions]
  return <Modal canClose={!w.busy} title="Confirm analysis setup" close={close}><div className="modal-body"><p>The configured model terms need researcher approval before this analysis can run. Already-approved terms will not prompt again.</p><details className="disclosure"><summary>View configured interaction terms</summary><div className="disclosure-body"><p>The enhanced model uses all six predictors plus these terms:</p><ul className="selected-terms">{terms.map(t=><li key={key(t)}>{t.join(' × ')}</li>)}</ul>{!terms.length && <p>No interactions are selected; both models will use main effects only.</p>}<p className="muted">Use only terms supported by your research. You can change the selection in Advanced Settings.</p></div></details><label className="checkbox-line"><input type="checkbox" checked={approved} disabled={w.busy} onChange={e=>setApproved(e.target.checked)}/>I approve this interaction specification for the analysis.</label>{w.error && <p className="inline-error" role="alert">{friendlyError(w.error)}</p>}</div><div className="modal-footer"><button className="button" disabled={w.busy} onClick={close}>Back to settings</button><button className="button primary" disabled={!approved || w.busy} onClick={confirm}>{w.busy ? 'Starting analysis...' : 'Continue'}</button></div></Modal>
}
