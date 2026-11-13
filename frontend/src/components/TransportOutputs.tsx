import { BusFront, Layers3, MapPin, TrainFront } from 'lucide-react'
import { useState } from 'react'
import type { Experiment, Row, TransportMode } from '../types'
import type { Workspace } from '../hooks/useExperiment'
import { Modal } from './Common'

export function DatasetTransport({s, w}: {s: Experiment; w: Workspace}) {
  const [open, setOpen] = useState(false)
  const [choice, setChoice] = useState('unknown')
  const counts = s.transport?.dataset_counts
  return <div className="dataset-transport">
    <div><BusFront size={16}/><span>{counts && counts.bus + counts.train > 0 ? `${counts.bus} bus / ${counts.train} train${counts.unspecified ? ` / ${counts.unspecified} unspecified` : ''}` : 'Bus / train not specified'}</span></div>
    {!s.transport?.column && <button className="text-button" disabled={w.busy || !s.transport} onClick={() => {setChoice(s.config.research_notes?.transport_mode || 'unknown');setOpen(true)}}>Set transport mode</button>}
    {open && <Modal title="Dataset transport mode" canClose={!w.busy} close={() => setOpen(false)}><form onSubmit={e => {e.preventDefault();void w.configure({...s.config, research_notes: {...s.config.research_notes, transport_mode: choice}}).then(() => setOpen(false)).catch(() => {})}}><div className="modal-body">
      <p className="muted">Identify the transport service these observations describe. This labels the output without adding a model predictor.</p>
      <label>Transport mode<select aria-label="Transport mode" value={choice} disabled={w.busy} onChange={e => setChoice(e.target.value)}><option value="unknown">Not specified</option><option value="bus">Bus only</option><option value="train">Train only</option><option value="mixed">Mixed bus and train</option></select></label>
      {choice === 'mixed' && <p className="decision-note">Mixed datasets need a Transport Mode column containing Bus or Train for each observation. Upload the labeled file to separate their outputs.</p>}
      <p className="section-caption">Saving creates a new revision and clears current results. Select Analyze Dataset again afterward.</p>
      {w.error && <p className="inline-error" role="alert">{w.error}</p>}
    </div><div className="modal-footer"><button className="button" type="button" disabled={w.busy} onClick={() => setOpen(false)}>Cancel</button><button className="button primary" disabled={w.busy}>Save transport mode</button></div></form></Modal>}
  </div>
}

export function observationMode(s: Experiment, row: Row | null): Exclude<TransportMode, 'all'> {
  if (!row) return 'unspecified'
  const value = s.transport?.column ? String(row[s.transport.column] || '').trim().toLowerCase() : s.config.research_notes?.transport_mode
  if (value === 'bus' || value === 'buses') return 'bus'
  if (['train', 'trains', 'rail', 'lrt', 'mrt', 'pnr'].includes(value || '')) return 'train'
  return 'unspecified'
}

export function TransportOutputs({s, mode, select}: {s: Experiment; mode: TransportMode; select: (value: TransportMode) => void}) {
  const counts = s.transport?.test_counts
  const choices = [
    {id: 'all' as const, label: 'All', icon: Layers3, count: s.test},
    {id: 'bus' as const, label: 'Bus', icon: BusFront, count: counts?.bus ?? 0},
    {id: 'train' as const, label: 'Train', icon: TrainFront, count: counts?.train ?? 0},
    ...(counts?.unspecified ? [{id: 'unspecified' as const, label: 'Unspecified', icon: MapPin, count: counts.unspecified}] : []),
  ]
  return <div className="transport-outputs">
    <div className="transport-tabs" role="group" aria-label="Transport output filters">{choices.map(({id, label, icon: Icon, count}) => <button key={id} className={`transport-tab mode-${id}`} aria-label={`${label} outputs`} aria-pressed={mode === id} disabled={!s.transport && id !== 'all'} onClick={() => select(id)}><Icon size={17} aria-hidden="true"/><span>{label}</span><small>{count}</small></button>)}</div>
    <p className="transport-filter-note">{!s.transport ? 'Restart the local server to enable transport views.' : counts?.unspecified ? 'Some observations have no transport label. Add a Transport Mode column or document a single-mode dataset in Advanced Settings.' : 'Choose a transport mode to explore its test observations.'}</p>
  </div>
}

export function TransportContext({s, row}: {s: Experiment; row: Row}) {
  const mode = observationMode(s, row)
  const Icon = mode === 'train' ? TrainFront : mode === 'bus' ? BusFront : Layers3
  const location = ['Transit Line', 'Route', 'Station'].filter(key => row[key] != null && String(row[key]).trim()).map(key => String(row[key])).join(' / ')
  return <div className={`transport-context mode-${mode}`}>
    <span className="transport-icon"><Icon size={25} strokeWidth={1.7}/></span>
    <div className="transport-context-copy"><strong>{mode === 'bus' ? 'Bus prediction' : mode === 'train' ? 'Train prediction' : 'Transport prediction'}</strong><span>{location || (mode === 'unspecified' ? 'Transport mode not specified' : 'Selected dataset observation')}</span></div>
    <span className="historical-label">Enhanced MLR</span>
  </div>
}
