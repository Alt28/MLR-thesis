import { useCallback, useEffect, useRef, useState } from 'react'
import { ArrowUpRight, BookOpen, BusFront, ChevronRight, GitBranch, Layers3, LoaderCircle, TrainFront } from 'lucide-react'
import { useExperiment } from './hooks/useExperiment'
import { AnalysisPage } from './pages/AnalysisPage'
import { PredictionPage } from './pages/PredictionPage'
import { AboutPage } from './pages/AboutPage'
import type { PredictionDataset } from './components/PredictionOnly'

const routeFromHash = () => location.hash === '#/about' ? 'about' : ['#/predict', '#/test'].includes(location.hash) ? 'prediction' : 'training'

export default function App() {
  const w = useExperiment()
  const [route, setRoute] = useState(routeFromHash)
  const [incoming, setIncoming] = useState<PredictionDataset | null>(null)
  const main = useRef<HTMLElement>(null)
  const consumeIncoming = useCallback(() => setIncoming(null), [])
  useEffect(() => {
    const update = () => {
      setRoute(routeFromHash())
      window.scrollTo({top: 0, behavior: 'instant'})
      requestAnimationFrame(() => main.current?.focus({preventScroll: true}))
    }
    addEventListener('hashchange', update)
    return () => removeEventListener('hashchange', update)
  }, [])
  const receivePrediction = (dataset: PredictionDataset) => {setIncoming(dataset); location.hash = '/predict'}
  const title = route === 'training' ? 'Training' : route === 'prediction' ? 'Test & Predict' : 'Methodology'
  return <div className="research-app lab-app">
    <a className="skip-link" href="#main-content" onClick={e => {e.preventDefault(); main.current?.focus()}}>Skip to content</a>
    <aside className="lab-sidebar">
      <a className="lab-brand" href="#/training" aria-label="Transit Lab home"><span className="lab-brand-icon"><img src="/favicon.svg" alt="" width={30} height={30}/></span><span>Transit Lab<small>TRANSPORT RESEARCH</small></span></a>
      <div className="sidebar-section-label">WORKSPACE</div>
      <nav aria-label="Main navigation"><a href="#/training" aria-current={route === 'training' ? 'page' : undefined}><Layers3 size={19}/><span>Training</span><ChevronRight size={14}/></a><a href="#/predict" aria-current={route === 'prediction' ? 'page' : undefined}><GitBranch size={19}/><span>Test & Predict</span><ChevronRight size={14}/></a><a href="#/about" aria-current={route === 'about' ? 'page' : undefined}><BookOpen size={19}/><span>Methodology</span><ChevronRight size={14}/></a></nav>
      <div className="sidebar-study"><span className="sidebar-section-label">THE STUDY</span><div className="sidebar-transit-icons"><BusFront size={21}/><span/><TrainFront size={21}/></div><strong>Better understand<br/>the waiting time.</strong><p>Compare Traditional and Enhanced Multiple Linear Regression.</p><a href="#/about">How it works<ArrowUpRight size={15}/></a></div>
      <div className="sidebar-connection"><span className={w.connected ? 'connection-dot' : 'connection-dot disconnected'}/><div>{w.connected ? 'Local workspace' : 'Connection unavailable'}<small>{w.connected ? 'Your analysis stays on this server' : 'Check that the local server is running'}</small></div></div>
    </aside>
    <div className="lab-workspace">
      <header className="lab-topbar"><div className="lab-breadcrumb"><span>Workspace</span><ChevronRight size={14}/><strong>{title}</strong></div><div className="lab-scope"><BusFront size={15}/><span>Bus</span><span className="scope-divider"/><TrainFront size={15}/><span>Train</span></div></header>
      <main ref={main} id="main-content" className="research-main" tabIndex={-1}>
        {w.connecting ? <div className="initial-loading" role="status"><LoaderCircle className="spinning"/>Opening your workspace...</div> : <><div data-workflow="training" hidden={route !== 'training'}><AnalysisPage w={w} onPredictionDataset={receivePrediction}/></div><div data-workflow="prediction" hidden={route !== 'prediction'}><PredictionPage w={w} incoming={incoming} consumeIncoming={consumeIncoming}/></div>{route === 'about' && <AboutPage/>}</>}
      </main>
      <footer className="research-footer"><span>Transit Lab · Waiting-time research</span><span>Traditional MLR / Enhanced MLR</span></footer>
    </div>
  </div>
}
