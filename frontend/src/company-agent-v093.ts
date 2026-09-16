/* PRINTFLOW Empresa e Agent v098
   Protege o token e apresenta comunicação e condição operacional real do Agent.
   Security baseline: dados da API são renderizados somente via textContent e o polling
   é encerrado quando o painel sai do DOM. */

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

function replaceChildren(parent: HTMLElement, ...children: Node[]) {
  parent.replaceChildren(...children)
}

function buildStatus(copy: { label: string; detail: string }) {
  const dot = document.createElement('span')
  dot.className = 'agent-link-dot'
  const text = document.createElement('div')
  text.className = 'agent-status-copy'
  const strong = document.createElement('strong')
  strong.textContent = copy.label
  const small = document.createElement('small')
  small.textContent = copy.detail
  text.append(strong, small)
  return [dot, text]
}

function renderOperation(operation: HTMLElement, data: AgentStatus) {
  const cycle = cycleCopy(data.status)
  const grid = document.createElement('div')
  grid.className = 'agent-operation-grid'

  const values = [
    ['Condição do ciclo', cycle.label, cycle.tone],
    ['Versão', data.version || 'Não informada', ''],
    ['Identificação', data.name || 'PRINTFLOW Agent', ''],
    ['Última comunicação', formatLastSeen(data.last_seen), ''],
  ]

  for (const [label, value, tone] of values) {
    const item = document.createElement('div')
    item.className = 'agent-operation-item'
    const caption = document.createElement('span')
    caption.textContent = label
    const strong = document.createElement('strong')
    strong.textContent = value
    if (tone) strong.dataset.cycleTone = tone
    item.append(caption, strong)
    grid.append(item)
  }

  const children: Node[] = [grid]
  if (data.last_error) {
    const error = document.createElement('div')
    error.className = 'agent-operation-error'
    const title = document.createElement('strong')
    title.textContent = 'Último erro'
    const detail = document.createElement('span')
    detail.textContent = data.last_error
    error.append(title, detail)
    children.push(error)
  }
  replaceChildren(operation, ...children)
}

function renderUnavailable(operation: HTMLElement, text: string) {
  const unavailable = document.createElement('div')
  unavailable.className = 'agent-operation-unavailable'
  unavailable.textContent = text
  replaceChildren(operation, unavailable)
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
    replaceChildren(status, ...buildStatus(copy))
    if (operation) renderOperation(operation, data)
  } catch {
    status.dataset.tone = 'offline'
    replaceChildren(status, ...buildStatus({ label: 'Status indisponível', detail: 'Não foi possível consultar o heartbeat agora.' }))
    if (operation) renderUnavailable(operation, 'Diagnóstico operacional temporariamente indisponível.')
  }
}

function enhanceCompanyAgent() {
  const headings = Array.from(document.querySelectorAll('h3'))
  const heading = headings.find((node) => node.textContent?.includes(TOKEN_LENGTH_HINT))
  if (!heading) return

  const panel = heading.closest('article.panel') as HTMLElement | null
  if (!panel || panel.dataset.v098 === 'ready') return

  const tokenBox = panel.querySelector('.token-box') as HTMLElement | null
  const actions = panel.querySelector('.row-actions') as HTMLElement | null
  if (!tokenBox || !actions) return

  const token = (tokenBox.textContent || '').trim()
  if (!token) return

  panel.dataset.v098 = 'ready'
  panel.classList.add('company-agent-link-panel')
  heading.textContent = 'Vinculação do Agent'

  const intro = panel.querySelector('p')
  if (intro) intro.textContent = 'Credencial segura usada exclusivamente para vincular o Agent a esta empresa.'

  const status = document.createElement('div')
  status.className = 'agent-link-status'
  replaceChildren(status, ...buildStatus({ label: 'Consultando Agent...', detail: 'Validando heartbeat operacional' }))
  tokenBox.before(status)

  const operation = document.createElement('section')
  operation.className = 'agent-operation'
  operation.setAttribute('aria-label', 'Diagnóstico operacional do Agent')
  renderUnavailable(operation, 'Carregando diagnóstico operacional...')
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
  const intervalId = window.setInterval(() => {
    if (!panel.isConnected) {
      window.clearInterval(intervalId)
      return
    }
    void loadAgentStatus(panel)
  }, 60_000)
}

const observer = new MutationObserver(enhanceCompanyAgent)
observer.observe(document.documentElement, { childList: true, subtree: true })

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', enhanceCompanyAgent, { once: true })
} else {
  enhanceCompanyAgent()
}
