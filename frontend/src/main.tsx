import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './styles.css'
import './dark.css'
import './analysis.css'

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>)
