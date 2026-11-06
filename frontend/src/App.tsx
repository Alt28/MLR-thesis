import { useEffect, useState } from 'react'
import { FlaskConical, LoaderCircle } from 'lucide-react'
import { useExperiment } from './hooks/useExperiment'
import { AnalysisPage } from './pages/AnalysisPage'
import { AboutPage } from './pages/AboutPage'

export default function App() {
  return <Workspace/>
}

function Workspace() {
  const w = useExperiment()
  const [about, setAbout] = useState(() => location.hash === '#/about')
  useEffect(() => {
    const update = () => setAbout(location.hash === '#/about')
    addEventListener('hashchange', update)
    return () => removeEventListener('hashchange', update)
  }, [])
  return <div className="research-app">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="research-header"><a className="research-brand" href="#/analyze"><FlaskConical size={23}/><span>Transit Lab<small>MLR research tool</small></span></a><nav aria-label="Main navigation"><a href="#/analyze" aria-current={!about ? 'page' : undefined}>Analyze</a><a href="#/about" aria-current={about ? 'page' : undefined}>About / Methodology</a></nav></header>
    <main id="main-content" className="research-main" tabIndex={-1}>
      {w.connecting ? <div className="initial-loading" role="status"><LoaderCircle className="spinning"/>Opening the analysis…</div> : <><div hidden={about}><AnalysisPage w={w}/></div>{about && <AboutPage/>}</>}
    </main>
    <footer className="research-footer"><span>Transportation data · Local analysis</span><span>Traditional & Enhanced Multiple Linear Regression</span></footer>
  </div>
}
