import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/tokens.css'
import './styles/global.css'
import App from './App.jsx'
import { registerAuthInterceptor } from './shared/security'
import { connectAuthToken } from './features/login/services/authService'

// Debe registrarse antes de cualquier llamada a la API
registerAuthInterceptor()
connectAuthToken()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
