import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import DeploymentStatus from './components/DeploymentStatus.tsx'
import './fiori-theme.css'
import './fiori-typography-fix.css'
import './fiori-polish-v2.css'
import './fiori-premium.css'
import './printflow-design-system.css'
import './login-enterprise.css'
import './brand-system.css'
import './theme-system.css'
import './theme-header-alignment.css'
import './compact-ui-v052.css'
import './dark-visibility-v053.css'
import './ux-polish-v054.css'
import './printers-clean-v055.css'
import './apple-dark-v056.css'
import './minimal-system-v060.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
    <DeploymentStatus />
  </StrictMode>,
)
