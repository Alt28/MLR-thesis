import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './analysis.css'
import './dark.css'
import './workspace.css'

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>)
