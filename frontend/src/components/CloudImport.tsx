import { ArrowRight, BusFront, Database, FileSpreadsheet, LibraryBig, LoaderCircle, Search, TrainFront } from 'lucide-react'
import { useState } from 'react'
import type { Workspace } from '../hooks/useExperiment'
import { datasetLibrary } from '../services/datasetLibrary'
import type { LibraryDataset } from '../services/datasetLibrary'
import { Modal } from './Common'
import { friendlyError } from '../services/presentation'

export function CloudImport({w, imported}: {w: Workspace; imported: () => void}) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const busy = w.busy || loadingId !== null
  const matches = datasetLibrary.filter(item => `${item.title} ${item.mode} ${item.filename}`.toLowerCase().includes(query.trim().toLowerCase()))
  const finish = () => {imported(); setOpen(false)}
  const select = async (item: LibraryDataset) => {
    setError(''); setLoadingId(item.id)
    try {await w.libraryImport(item.filename); finish()}
    catch (e) {
      const message = e instanceof Error ? e.message : 'Could not import this dataset. Please try again.'
      setError(`${item.title}: ${message.includes('Missing required columns:') ? friendlyError(message, 'dataset') : message}`)
    }
    finally {setLoadingId(null)}
  }
  return <>
    <button className="button cloud-import-trigger" disabled={w.busy} onClick={() => {setError(''); setQuery(''); setOpen(true)}}><LibraryBig size={18}/>Dataset Library</button>
    {open && <Modal title="Dataset library on this server" className="cloud-import-modal dataset-library-modal" close={() => setOpen(false)} canClose={!busy}>
      <div className="library-navigation"><p>Example datasets bundled with Transit Lab. Select one to import it directly; this is not a connection to your cloud storage account. Use Upload Dataset for your own files.</p></div>
        <div className="library-search-area">
          <label className="library-search"><Search size={18} aria-hidden="true"/><input aria-label="Search library datasets" type="search" placeholder="Search by name or transport mode…" value={query} disabled={busy} onChange={e => {setQuery(e.target.value); setError('')}}/></label>
          <p className="library-disclosure">No download or re-upload needed. Files must pass the required-column checks.</p>
        </div>
        {error && <div role="alert" className="inline-error library-import-error">{error}</div>}
        <div className="library-files" aria-label="Available datasets" aria-busy={busy}>
          {matches.map(item => <button key={item.id} className="library-file" disabled={busy} onClick={() => void select(item)} aria-label={`Import ${item.title}`}>
            <span className={`library-file-icon ${item.mode === 'Train' ? 'train' : ''}`} aria-hidden="true">{loadingId === item.id ? <LoaderCircle size={23} className="spinning"/> : item.mode === 'Bus' ? <BusFront size={23}/> : item.mode === 'Train' ? <TrainFront size={23}/> : <FileSpreadsheet size={23}/>}</span>
            <span className="library-file-copy"><span className="library-file-title">{item.title}</span><span className="library-file-description">{item.filename}</span><span className="library-file-meta"><span className={item.kind === 'reference' ? 'library-reference-badge' : 'library-demo-badge'}>{item.kind === 'reference' ? 'Incomplete for analysis' : item.kind === 'demo' ? 'Synthetic demo' : 'Prototype only'}</span>{item.records.toLocaleString()} {item.recordLabel} · {item.filename.endsWith('.csv') ? 'CSV' : 'XLSX'}</span>{item.kind !== 'reference' && item.note && <span className="library-file-note">{item.note}</span>}</span>
            <span className="library-select">{loadingId === item.id ? 'Loading…' : 'Import'}<ArrowRight size={16}/></span>
          </button>)}
          {!matches.length && <div className="library-empty"><Search size={24}/><strong>No datasets found</strong><p>Try searching for bus or train.</p><button className="text-button" onClick={() => setQuery('')}>Clear search</button></div>}
          {busy && <p role="status" className="cloud-import-status"><LoaderCircle size={17} className="spinning"/>Loading and checking your dataset…</p>}
        </div>
        <div className="library-footer"><span><Database size={14}/>Stored on this Transit Lab server</span><span role="status">{matches.length} {matches.length === 1 ? 'dataset' : 'datasets'}</span></div>
    </Modal>}
  </>
}
