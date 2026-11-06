import busSprite from '../assets/loading-bus.svg'
import { useEffect, useState } from 'react'
import { Pause, Play } from 'lucide-react'

/** Decorative motion only; the parent loading status announces actual work. */
export function LoadingBus() {
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches)
  const [choice, setChoice] = useState<boolean | null>(() => {
    try {const saved = localStorage.getItem('transit-bus-motion'); return saved === 'on' ? true : saved === 'off' ? false : null}
    catch {return null}
  })
  useEffect(() => {
    const media = matchMedia('(prefers-reduced-motion: reduce)')
    const changed = () => setReduced(media.matches)
    media.addEventListener('change', changed)
    return () => media.removeEventListener('change', changed)
  }, [])
  const moving = choice ?? !reduced
  const toggle = () => {
    setChoice(!moving)
    try {localStorage.setItem('transit-bus-motion', moving ? 'off' : 'on')} catch { /* Animation remains usable without storage. */ }
  }
  return <div className="bus-loader" data-motion={moving ? 'on' : 'off'}>
    <div className="loading-bus-scene" aria-hidden="true">
      <div className="bus-speed-lines"><i/><i/><i/></div>
      <div className="bus-travel">
        <div className="bus-sprite"><img src={busSprite} alt="" width="160" height="130"/><span className="bus-wheel"/><span className="bus-wheel rear"/></div>
        <div className="bus-shadow"/>
      </div>
      <div className="bus-road"><span/></div>
    </div>
    <button type="button" className="text-button bus-motion-toggle" onClick={toggle} aria-label={moving ? 'Pause bus animation' : 'Play bus animation'}>{moving ? <Pause size={13}/> : <Play size={13}/>} {moving ? 'Pause animation' : 'Play animation'}</button>
  </div>
}
