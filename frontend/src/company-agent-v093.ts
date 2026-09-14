/* PRINTFLOW Empresa e Agent v093
   Protege visualmente o token do Agent sem alterar o fluxo/API existente. */

const TOKEN_LENGTH_HINT = '43 caracteres'

function maskToken(token: string) {
  const suffix = token.slice(-4)
  return `•••••••••••••••••••••••••••••••••••••••${suffix}`
}

function enhanceCompanyAgent() {
  const headings = Array.from(document.querySelectorAll('h3'))
  const heading = headings.find((node) => node.textContent?.includes(TOKEN_LENGTH_HINT))
  if (!heading) return

  const panel = heading.closest('article.panel') as HTMLElement | null
  if (!panel || panel.dataset.v093 === 'ready') return

  const tokenBox = panel.querySelector('.token-box') as HTMLElement | null
  const actions = panel.querySelector('.row-actions') as HTMLElement | null
  if (!tokenBox || !actions) return

  const token = (tokenBox.textContent || '').trim()
  if (!token) return

  panel.dataset.v093 = 'ready'
  panel.classList.add('company-agent-link-panel')
  heading.textContent = 'Vinculação do Agent'

  const intro = panel.querySelector('p')
  if (intro) intro.textContent = 'Credencial segura usada exclusivamente para vincular o Agent a esta empresa.'

  const status = document.createElement('div')
  status.className = 'agent-link-status'
  status.innerHTML = '<span class="agent-link-dot"></span><div><strong>Token ativo</strong><small>Agent autorizado para esta empresa</small></div>'
  tokenBox.before(status)

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
}

const observer = new MutationObserver(enhanceCompanyAgent)
observer.observe(document.documentElement, { childList: true, subtree: true })

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', enhanceCompanyAgent)
} else {
  enhanceCompanyAgent()
}
