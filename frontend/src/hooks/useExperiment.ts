import { useCallback, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Experiment, ExperimentListItem, ResearchConfig } from '../types'

export function useExperiment() {
  const [experiment, setExperiment] = useState<Experiment | null>(null)
  const [experiments, setExperiments] = useState<ExperimentListItem[]>([])
  const [working, setWorking] = useState(false)
  const [operation, setOperation] = useState<'upload' | 'analyze' | 'saving' | null>(null)
  const [connecting, setConnecting] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [connected, setConnected] = useState(false)
  const accept = useCallback((s: Experiment) => { setExperiment(s); localStorage.setItem('transit-experiment', s.id); setConnected(true) }, [])
  useEffect(() => {
    let alive = true
    api.list().then(async list => {
      if (!alive) return
      setExperiments(list); setConnected(true)
      const remembered = localStorage.getItem('transit-experiment')
      const id = list.find(s => s.id === remembered)?.id ?? list[0]?.id
      if (id) { const result = await api.get(id); if (alive) accept(result) }
    }).catch(e => { if (alive) setError(e.message) }).finally(() => { if (alive) setConnecting(false) })
    return () => { alive = false }
  }, [accept])
  useEffect(() => {
    if (experiment?.status !== 'running') return
    let active = true
    const timer = setInterval(() => {
      api.get(experiment.id).then(s => {
        if (!active) return
        accept(s)
        if (s.status === 'error') setError(s.error || 'Training failed.')
        if (s.status === 'complete') setNotice('Experiment complete. Results and export files are ready.')
        if (s.status === 'partial') setNotice('Model trained. Train the remaining model to complete the comparison.')
      }).catch(e => { if (active) setError(e.message) })
    }, 1000)
    return () => { active = false; clearInterval(timer) }
  }, [experiment?.id, experiment?.status, accept])
  const perform = async (task: () => Promise<void>, operation: 'upload' | 'analyze' | 'saving' = 'saving') => {
    setWorking(true); setOperation(operation); setError(''); setNotice('')
    try { await task() } catch (e) { setError(e instanceof Error ? e.message : 'The operation failed.'); throw e } finally { setWorking(false); setOperation(null) }
  }
  const upload = (file: File) => perform(async () => { accept(await api.upload(file)); setExperiments(await api.list()); setNotice('Dataset ready. Select Analyze Dataset to continue.') }, 'upload')
  const select = (id: string) => perform(async () => accept(await api.get(id)))
  const cloudImport = (provider: 'google' | 'onedrive', url: string) => perform(async () => {
    accept(await api.cloudImport(provider, url)); setExperiments(await api.list())
    setNotice('Cloud dataset imported. Select Analyze Dataset to continue.')
  }, 'upload')
  const libraryImport = (filename: string) => perform(async () => {
    accept(await api.libraryImport(filename)); setExperiments(await api.list())
    setNotice('Demo dataset ready. Select Analyze Dataset to test the workflow. These are synthetic observations.')
  }, 'upload')
  const configure = (config: ResearchConfig, approve = false) => perform(async () => {
    if (!experiment) return
    accept(await api.configure(experiment, config, approve)); setNotice('Settings saved as a new revision. Train the models again to update results.')
  })
  const train = (selection: string) => perform(async () => {
    if (!experiment) return
    await api.train(experiment, selection); accept(await api.get(experiment.id))
  })
  const analyze = (approve = false, retain = false, reason = '') => perform(async () => {
    if (!experiment) return
    await api.analyze(experiment, approve, retain, reason)
    accept(await api.get(experiment.id))
  }, 'analyze')
  const review = (id: string, action: string, reason: string, corrections: Record<string, string | number>) => perform(async () => {
    if (!experiment) return
    accept(await api.review(experiment, id, action, reason, corrections)); setNotice('Review decision recorded. Previous model results have been cleared.')
  })
  return { experiment, experiments, operation, upload, cloudImport, libraryImport, select, configure, train, analyze, review, working, connecting, connected, busy: working || experiment?.status === 'running', error, notice, setError, setNotice }
}
export type Workspace = ReturnType<typeof useExperiment>
