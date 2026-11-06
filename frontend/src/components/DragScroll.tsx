import { useEffect, useRef, useState, type ReactNode } from 'react'

export function DragScroll({children}: {children: ReactNode}) {
  const container = useRef<HTMLDivElement>(null)
  const drag = useRef<{id: number; x: number; left: number} | null>(null)
  const moved = useRef(false)
  const [overflow, setOverflow] = useState(false)
  const [dragging, setDragging] = useState(false)
  useEffect(() => {
    const element = container.current!
    const observer = new ResizeObserver(() => setOverflow(element.scrollWidth > element.clientWidth + 1))
    observer.observe(element)
    if (element.firstElementChild) observer.observe(element.firstElementChild)
    return () => observer.disconnect()
  }, [])
  const finish = () => {drag.current = null; setDragging(false)}
  return <>
    {overflow && <p className="table-pan-hint">Drag the table left or right to see more columns.</p>}
    <div ref={container} className={`table-scroll draggable-table${overflow ? ' can-pan' : ''}${dragging ? ' is-panning' : ''}`}
      tabIndex={overflow ? 0 : undefined} role={overflow ? 'region' : undefined}
      aria-label={overflow ? 'Scrollable table: drag left or right, or use the arrow keys' : undefined}
      onPointerDown={e => {
        moved.current = false
        if (!overflow || e.pointerType !== 'mouse' || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return
        if ((e.target as HTMLElement).closest('button, a, input, select, textarea, [contenteditable="true"]')) return
        const element = e.currentTarget
        const box = element.getBoundingClientRect()
        if (e.clientY >= box.top + element.clientHeight || e.clientX >= box.left + element.clientWidth) return
        e.preventDefault()
        element.focus({preventScroll: true})
        drag.current = {id: e.pointerId, x: e.clientX, left: element.scrollLeft}
        element.setPointerCapture(e.pointerId)
        setDragging(true)
      }}
      onPointerMove={e => {
        const start = drag.current
        if (!start || start.id !== e.pointerId) return
        const distance = e.clientX - start.x
        if (!moved.current && Math.abs(distance) < 4) return
        moved.current = true
        e.preventDefault()
        e.currentTarget.scrollLeft = start.left - distance
      }}
      onPointerUp={e => {
        if (drag.current?.id !== e.pointerId) return
        finish()
        if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId)
      }}
      onPointerCancel={finish} onLostPointerCapture={finish}
      onClickCapture={e => {if (moved.current && e.detail > 0) {e.preventDefault(); e.stopPropagation(); moved.current = false}}}
    >{children}</div>
  </>
}
