/* PRINTFLOW Empresa e Agent v095
   Protege o token e apresenta comunicação e condição operacional real do Agent. */

const TOKEN_LENGTH_HINT = '43 caracteres'
const API_URL = (import.meta.env.VITE_API_URL || 'https://printflow-api-genesis.onrender.com').replace(/\/$/, '')

type AgentStatus = {
  online: boolean
  stale: boolean
  communication_state: 'healthy' | 'stale' | 'offline' | 'never_seen' | 'inactive' | string
  status?: string | null
  name?: string | null
  version?: string | null
  last_seen?: string | null
  last_error?: string | null
}

function maskToken(token: string) {
  const suffix = token.slice(-4)
  return `•••••••••••••••••••••••••••••••••••••••${suffix}`
}

function formatLastSeen(value?: string | null) {
  if (!value) return 'Nenhuma comunicação registrada'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'Horário indisponível'
  return date.toLocaleString('pt-BR')
}

function statusCopy(data: AgentStatus) {
  if (data.online) return { label: 'Agent Online', detail: 'Comunicação saudável', tone: 'online' }
  if (data.stale) return { label: 'Agent em atenção', detail: 'Heartbeat atrasado', tone: 'stale' }
  if (data.communication_state === 'never_seen') return { label: 'Aguardando Agent', detail: 'Primeira comunicação ainda não recebida', tone: 'offline' }
  if (data.communication_state === 'inactive') return { label: 'Agent inativo', detail: 'Empresa inativa', tone: 'offline' }
  return { label: 'Agent Offline', detail: 'Sem comunicação recente', tone: 'offline' }
}

function cycleCopy(status?: string | null) {
  const value = (status || '').toLowerCase()
  if (value === 'healthy') return { label: 'Saudável', tone: 'ok' }
  if (value === 'slow') return { label: 'Ciclo lento', tone: 'warn' }
  if (value === 'error') return { label: 'Falha no ciclo', tone: 'error' }
  if (value === 'running') return { label: 'Em execução', tone: 'running' }
  return { label: 'Sem diagnóstico', tone: 'neutral' }
}

function operationalPanel(data: AgentStatus) {
  const cycle = cycleCopy(data.status)
  const error = data.last_error
    ? `<div class="agent-operation-error"><strong>Último erro</strong><span>${data.last_error}</span></div>`
    : ''

  return `
    <div class="agent-operation-grid">
      <div class="agent-operation-item">
        <span>Condição do ciclo</span>
        <strong data-cycle-tone="${cycle.tone}">${cycle.label}</strong>
      </div>
      <div class="agent-operation-item">
        <span>Versão</span>
        <strong>${data.version || 'Não informada'}</strong>
      </div>
      <div class="agent-operation-item">
        <span>Identificação</span>
        <strong>${data.name || 'PRINTFLOW Agent'}</strong>
      </div>
      <div class="agent-operation-item">
        <span>Última comunicação</span>
        <strong>${formatLastSeen(data.last_seen)}</strong>
      </div>
    </div>
    ${error}`
}

async function loadAgentStatus(panel: HTMLElement) {
  const status = panel.querySelector('.agent-link-status') as HTMLElement | null
  const operation = panel.querySelector('.agent-operation') as HTMLElement | null
  if (!status) return

  try {
    const previewToken = sessionStorage.getItem('printflow_preview_token')
    const response = await fetch(`${API_URL}/api/v1/companies/current/agent-status`, {
      credentials: 'include',
      headers: previewToken ? { Authorization: `Bearer ${previewToken}` } : {},
    })
    if (!response.ok) throw new Error('Falha ao consultar Agent')
    const data = await response.json() as AgentStatus
    const copy = statusCopy(data)

    status.dataset.tone = copy.tone
    status.innerHTML = `
      <span class="agent-link-dot"></span>
      <div class="agent-status-copy">
        <strong>${copy.label}</strong>
        <small>${copy.detail}</small>
      </div>`

    if (operation) operation.innerHTML = operationalPanel(data)
  } catch {
    status.dataset.tone = 'offline'
    status.innerHTML = '<span class="agent-link-dot"></span><div><strong>Status indisponível</strong><small>Não foi possível consultar o heartbeat agora.</small></div>'
    if (operation) operation.innerHTML = '<div class="agent-operation-unavailable">Diagnóstico operacional temporariamente indisponível.</div>'
  }
}

function enhanceCompanyAgent() {
  const headings = Array.from(document.querySelectorAll('h3'))
  const heading = headings.find((node) => node.textContent?.includes(TOKEN_LENGTH_HINT))
  if (!heading) return

  const panel = heading.closest('article.panel') as HTMLElement | null
  if (!panel || panel.dataset.v095 === 'ready') return

  const tokenBox = panel.querySelector('.token-box') as HTMLElement | null
  const actions = panel.querySelector('.row-actions') as HTMLElement | null
  if (!tokenBox || !actions) return

  const token = (tokenBox.textContent || '').trim()
  if (!token) return

  panel.dataset.v095 = 'ready'
  panel.classList.add('company-agent-link-panel')
  heading.textContent = 'Vinculação do Agent'

  const intro = panel.querySelector('p')
  if (intro) intro.textContent = 'Credencial segura usada exclusivamente para vincular o Agent a esta empresa.'

  const status = document.createElement('div')
  status.className = 'agent-link-status'
  status.innerHTML = '<span class="agent-link-dot"></span><div><strong>Consultando Agent...</strong><small>Validando heartbeat operacional</small></div>'
  tokenBox.before(status)

  const operation = document.createElement('section')
  operation.className = 'agent-operation'
  operation.setAttribute('aria-label', 'Diagnóstico operacional do Agent')
  operation.innerHTML = '<div class="agent-operation-unavailable">Carregando diagnóstico operacional...</div>'
  status.after(operation)

  tokenBox.textContent = maskToken(token)
  tokenBox.setAttribute('aria-label', 'Token do Agent mascarado')

  let visible = false
  const toggle = document.createElement('button')
  toggle.type = 'button'
  toggle.className = 'token-toggle-v093'
  toggle.textContent = 'Mostrar'
  toggle.addEventListener('click', () => {
    visible = !visible
    tokenBox.textContent = visible ? token : maskToken(token)
    toggle.textContent = visible ? 'Ocultar' : 'Mostrar'
    tokenBox.setAttribute('aria-label', visible ? 'Token do Agent visível' : 'Token do Agent mascarado')
  })
  actions.prepend(toggle)

  const tariff = panel.querySelector('.tariff-box') as HTMLElement | null
  if (tariff) tariff.remove()

  void loadAgentStatus(panel)
  window.setInterval(() => void loadAgentStatus(panel), 60_000)
}

const observer = new MutationObserver(enhanceCompanyAgent)
observer.observe(document.documentElement, { childList: true, subtree: true })

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', enhanceCompanyAgent)
} else {
  enhanceCompanyAgent()
}
