import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './App.css'
import { TelemetryProvider } from './context/metrics.jsx'
import { Toaster } from 'react-hot-toast'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <TelemetryProvider>
      <Toaster 
        position="top-right" 
        containerStyle={{
          top: '4.5rem',
          right: '1.5rem',
          zIndex: 99999,
        }}
      />
      <App />
    </TelemetryProvider>
  </StrictMode>,
)