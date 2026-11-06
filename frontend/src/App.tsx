import { useEffect, useState, type FormEvent } from 'react'
import { FlaskConical, LoaderCircle, LockKeyhole } from 'lucide-react'
import { useExperiment } from './hooks/useExperiment'
import { AnalysisPage } from './pages/AnalysisPage'
import { AboutPage } from './pages/AboutPage'
import { api } from './services/api'

export default function App() {
  const [access, setAccess] = useState<'checking' | 'password' | 'open' | 'error'>('checking')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    api.authStatus().then(status => {
      if (!active) return
      if (!status.required || status.authenticated) setAccess('open')
      else { api.clearPassword(); setAccess('password') }
    }).catch(e => {
      if (!active) return
      setError(e instanceof Error ? e.message : 'Could not connect to the analysis server.')
      setAccess('error')
    })
    const expired = () => {
      setPassword('')
      setError('Your workspace password is no longer valid. Enter it again to continue.')
      setAccess('password')
    }
    addEventListener('mlr-auth-expired', expired)
    return () => {active = false; removeEventListener('mlr-auth-expired', expired)}
  }, [])
  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    try {
      await api.authenticate(password)
      setAccess('open')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to unlock the workspace.')
    }
  }

  if (access === 'checking') return <main className="access-screen"><div role="status"><LoaderCircle className="spinning"/> Connecting to the analysis server…</div></main>
  if (access === 'error') return <main className="access-screen"><section className="access-card"><FlaskConical size={28}/><h1>Transit Lab</h1><p role="alert">{error}</p><button className="button primary" onClick={() => location.reload()}>Try again</button></section></main>
  if (access === 'password') return <main className="access-screen"><form className="access-card" onSubmit={login}><FlaskConical size={28}/><h1>Transit Lab</h1><p>This research workspace is password-protected. Enter its password to access datasets and experiments.</p><label htmlFor="workspace-password"><LockKeyhole size={15}/> Workspace password</label><input id="workspace-password" type="password" autoComplete="current-password" maxLength={4096} required value={password} onChange={e => setPassword(e.target.value)}/>{error && <p className="inline-error" role="alert">{error}</p>}<button className="button primary" disabled={!password}>Unlock workspace</button><small>Access is shared with anyone who has this password. Do not use this workspace for confidential or identifying data.</small></form></main>
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
