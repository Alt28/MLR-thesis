import { ArrowRight, BusFront, Database, FileSpreadsheet, LibraryBig, LoaderCircle, Search, TrainFront } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { Workspace } from '../hooks/useExperiment'
import { api, ApiError } from '../services/api'
import type { LibraryDataset } from '../services/datasetLibrary'
import { Modal } from './Common'
import { friendlyError } from '../services/presentation'

export function CloudImport({w, upload}: {w: Workspace; upload: (file: File) => Promise<boolean>}) {
  const [open, setOpen] = useState(false)
  const [datasetLibrary, setLibrary] = useState<LibraryDataset[]>([])
  const [listing, setListing] = useState(false)
  useEffect(() => {
    if (!open) return
    let active = true; setListing(true); setLibrary([])
    api.library().then(items => {if (active) setLibrary(items)}).catch(e => {
      if(active) setError(e instanceof ApiError && e.status === 404
        ? 'This window is connected to an older server. Open Start MLR System.bat again and use the browser window it opens. Your collected files are still saved.'
        : e.message)
    }).finally(() => {if(active) setListing(false)})
    return () => {active = false}
  }, [open])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const busy = w.busy || loadingId !== null
  const matches = datasetLibrary.filter(item => `${item.title} ${item.mode} ${item.filename}`.toLowerCase().includes(query.trim().toLowerCase()))
  const select = async (item: LibraryDataset) => {
    setError(''); setLoadingId(item.id)
    try {
      const file = await api.libraryFile(item)
      if (!await upload(file)) throw new Error('The file needs attention. Close this window to see the import message.')
      setOpen(false)
    }
    catch (e) {
      const message = e instanceof Error ? e.message : 'Could not import this dataset. Please try again.'
      setError(`${item.title}: ${message.includes('Missing required columns:') ? friendlyError(message, 'dataset') : message}`)
    }
    finally {setLoadingId(null)}
  }
  return <>
    <button className="button cloud-import-trigger" disabled={w.busy} onClick={() => {setError(''); setQuery(''); setOpen(true)}}><LibraryBig size={18}/>Dataset Library</button>
    {open && <Modal title="Dataset library on this server" className="cloud-import-modal dataset-library-modal" close={() => setOpen(false)} canClose={!busy}>
      <div className="library-navigation"><p>Select a dataset from the library, or use Upload Dataset to choose your own file.</p></div>
        <div className="library-search-area">
          <label className="library-search"><Search size={18} aria-hidden="true"/><input aria-label="Search library datasets" type="search" placeholder="Search by name or transport mode…" value={query} disabled={busy} onChange={e => {setQuery(e.target.value); setError('')}}/></label>
          <p className="library-disclosure">Files are checked before import. Source notes remain available with the dataset.</p>
        </div>
        {error && <div role="alert" className="inline-error library-import-error">{error}</div>}
        <div className="library-files" aria-label="Available datasets" aria-busy={busy}>
          {matches.map(item => <button key={item.id} className="library-file" disabled={busy} onClick={() => void select(item)} aria-label={`Import ${item.title}`}>
            <span className={`library-file-icon ${item.mode === 'Train' ? 'train' : ''}`} aria-hidden="true">{loadingId === item.id ? <LoaderCircle size={23} className="spinning"/> : item.mode === 'Bus' ? <BusFront size={23}/> : item.mode === 'Train' ? <TrainFront size={23}/> : <FileSpreadsheet size={23}/>}</span>
            <span className="library-file-copy"><span className="library-file-title">{item.title}</span><span className="library-file-description">{item.filename}</span><span className="library-file-meta">{item.records.toLocaleString()} {item.recordLabel} · {item.filename.endsWith('.csv') ? 'CSV' : 'XLSX'}</span>{item.note && <span className="library-file-note">{item.note}</span>}</span>
            <span className="library-select">{loadingId === item.id ? 'Loading…' : 'Import'}<ArrowRight size={16}/></span>
          </button>)}
          {listing && <p role="status">Loading collected datasets...</p>}
          {!listing && !error && !matches.length && <div className="library-empty"><Search size={24}/><strong>No datasets found</strong><p>No collected files match this search. Use Upload Dataset or register the ETL output with this server.</p><button className="text-button" onClick={() => setQuery('')}>Clear search</button></div>}
          {busy && <p role="status" className="cloud-import-status"><LoaderCircle size={17} className="spinning"/>Loading and checking your dataset…</p>}
        </div>
        <div className="library-footer"><span><Database size={14}/>Stored on this Transit Lab server</span><span role="status">{error ? 'Library unavailable' : listing ? 'Loading...' : `${matches.length} ${matches.length === 1 ? 'dataset' : 'datasets'}`}</span></div>
    </Modal>}
  </>
}
