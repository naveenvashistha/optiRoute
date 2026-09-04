import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './App.css'
import { TelemetryProvider } from './context/metrics.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <TelemetryProvider>
      <App />
    </TelemetryProvider>
  </StrictMode>,
)
