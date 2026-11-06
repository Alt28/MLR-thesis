import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ArrowRight, Database, Download, Info, X } from 'lucide-react'
import type { Experiment } from '../types'
import { figureUrl } from '../services/api'

export const format = (value: unknown, digits = 3) => value == null ? '—' : typeof value === 'number' ? value.toLocaleString(undefined, {maximumFractionDigits: digits}) : typeof value === 'boolean' ? value ? 'Yes' : 'No' : String(value)
export function Badge({ children, tone = 'neutral' }: {children: ReactNode; tone?: string}) { return <span className={`badge ${tone}`}>{children}</span> }
export function Panel({ title, subtitle, children, action, className = '' }: {title?: string; subtitle?: string; children: ReactNode; action?: ReactNode; className?: string}) {
  return <section className={`panel ${className}`}>{title && <div className="panel-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>}{children}</section>
}
export function InfoNote({children}: {children: ReactNode}) {return <div className="info-note"><Info size={17}/><div>{children}</div></div>}
export function Empty({title = 'Start with a recorded dataset', text = 'Import a CSV or Excel file to begin your research workflow.', action, compact = false}: {title?: string; text?: string; action?: ReactNode; compact?: boolean}) {
  return <div className={`empty ${compact ? 'compact' : ''}`}><div className="empty-icon"><Database size={27} strokeWidth={1.5}/></div><h3>{title}</h3><p>{text}</p>{action}</div>
}
export function NeedData({onImport}: {onImport: () => void}) {return <Panel><Empty action={<button className="button primary" onClick={onImport}>Import dataset <ArrowRight size={16}/></button>}/></Panel>}
export function Metric({label, value, detail, accent = false, icon}: {label: string; value: unknown; detail?: string; accent?: boolean; icon?: ReactNode}) {return <div className={`metric ${accent ? 'accent' : ''}`}><div className="metric-label"><span>{label}</span>{icon}</div><strong>{format(value)}</strong><small>{detail}</small></div>}
export function Chart({s, name, title}: {s: Experiment; name: string; title: string}) {
  return <Panel title={title} action={s.figures.includes(name) && <a className="icon-button" href={figureUrl(s, name)} download={`${name}.png`} aria-label={`Download ${title}`}><Download size={16}/></a>}>
    {s.figures.includes(name) ? <img className="research-chart" src={figureUrl(s, name, true)} alt={title}/> : <Empty compact title="No chart yet" text="Train both models to generate this figure from held-out observations."/>}
  </Panel>
}
export function Modal({title, children, close, className = '', canClose = true}: {title: string; children: ReactNode; close: () => void; className?: string; canClose?: boolean}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()
  const [closing, setClosing] = useState(false)
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestClose = () => {
    if (!canClose || closeTimer.current) return
    if (matchMedia('(prefers-reduced-motion: reduce)').matches) {close(); return}
    setClosing(true)
    closeTimer.current = setTimeout(() => {closeTimer.current = null; close(); setClosing(false)}, 130)
  }
  useEffect(() => {
    const dialog = ref.current
    const previous = document.activeElement as HTMLElement | null
    dialog?.showModal()
    return () => {
      if (closeTimer.current) clearTimeout(closeTimer.current)
      dialog?.close()
      queueMicrotask(() => {
        if (previous?.isConnected && !previous.closest('dialog:not([open])')) previous.focus({preventScroll: true})
      })
    }
  }, [])
  return <dialog ref={ref} aria-labelledby={titleId} className={`modal ${className}`} data-closing={closing || undefined} onCancel={e => {e.preventDefault(); requestClose()}} onClick={e => {if (e.target === ref.current) {const box = ref.current.getBoundingClientRect(); if (e.clientX < box.left || e.clientX > box.right || e.clientY < box.top || e.clientY > box.bottom) requestClose()}}}><div className="modal-heading"><h2 id={titleId}>{title}</h2><button className="icon-button" onClick={requestClose} disabled={!canClose || closing} aria-label="Close dialog"><X size={20}/></button></div>{children}</dialog>
}
