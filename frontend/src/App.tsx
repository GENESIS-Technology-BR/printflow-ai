import { useEffect, useState } from "react"
import "./App.css"

type Company = {
  id: number
  uuid: string
  name: string
  active: boolean
  created_at: string
}

function App() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [apiOnline, setApiOnline] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadDashboard() {
      try {
        const [healthResponse, companiesResponse] = await Promise.all([
          fetch("/health"),
          fetch("/api/v1/companies"),
        ])

        setApiOnline(healthResponse.ok)

        if (companiesResponse.ok) {
          setCompanies(await companiesResponse.json())
        }
      } catch {
        setApiOnline(false)
      } finally {
        setLoading(false)
      }
    }

    loadDashboard()
  }, [])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">P</div>
          <div>
            <strong>PRINTFLOW AI</strong>
            <span>GENESIS Platform</span>
          </div>
        </div>

        <nav className="navigation">
          <button className="nav-item active">▦ Dashboard</button>
          <button className="nav-item">▣ Empresas</button>
          <button className="nav-item">▧ Impressoras</button>
          <button className="nav-item">◉ Agentes</button>
          <button className="nav-item">△ Alertas</button>
          <button className="nav-item">≡ Relatórios</button>
        </nav>

        <div className="sidebar-footer">
          <span className={`status-dot ${apiOnline ? "online" : "offline"}`} />
          API {apiOnline ? "Online" : "Offline"}
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Visão geral</p>
            <h1>Dashboard</h1>
          </div>

          <div className="user-card">
            <div className="avatar">GT</div>
            <div>
              <strong>GENESIS Technology</strong>
              <span>Administrador</span>
            </div>
          </div>
        </header>

        <section className="hero">
          <div>
            <span className="hero-badge">PRINTFLOW AI · v0.2</span>
            <h2>Gestão inteligente do ambiente de impressão</h2>
            <p>
              Acompanhe empresas, impressoras, agentes e alertas em uma única
              plataforma.
            </p>
          </div>

          <div className={`system-status ${apiOnline ? "online" : "offline"}`}>
            <span />
            {apiOnline ? "Sistema operacional" : "API indisponível"}
          </div>
        </section>

        <section className="metrics">
          <article className="metric-card">
            <span className="metric-icon">▣</span>
            <div>
              <p>Empresas</p>
              <strong>{loading ? "..." : companies.length}</strong>
              <small>cadastradas na plataforma</small>
            </div>
          </article>

          <article className="metric-card">
            <span className="metric-icon">▧</span>
            <div>
              <p>Impressoras</p>
              <strong>0</strong>
              <small>aguardando Agent</small>
            </div>
          </article>

          <article className="metric-card">
            <span className="metric-icon">◉</span>
            <div>
              <p>Agentes</p>
              <strong>0</strong>
              <small>nenhum instalado</small>
            </div>
          </article>

          <article className="metric-card">
            <span className="metric-icon">△</span>
            <div>
              <p>Alertas</p>
              <strong>0</strong>
              <small>ambiente estável</small>
            </div>
          </article>
        </section>

        <section className="dashboard-grid">
          <article className="panel companies-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Organizações</p>
                <h3>Empresas cadastradas</h3>
              </div>
              <button className="primary-button">Nova empresa</button>
            </div>

            {loading ? (
              <div className="empty-state">Carregando empresas...</div>
            ) : companies.length === 0 ? (
              <div className="empty-state">Nenhuma empresa cadastrada.</div>
            ) : (
              <div className="company-list">
                {companies.map((company) => (
                  <div className="company-row" key={company.uuid}>
                    <div className="company-logo">
                      {company.name.slice(0, 2).toUpperCase()}
                    </div>

                    <div className="company-info">
                      <strong>{company.name}</strong>
                      <span>ID #{company.id}</span>
                    </div>

                    <span className={company.active ? "badge-active" : "badge-inactive"}>
                      {company.active ? "Ativa" : "Inativa"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </article>

          <article className="panel agent-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Coleta automática</p>
                <h3>PRINTFLOW Agent</h3>
              </div>
            </div>

            <div className="agent-illustration">◉</div>
            <h4>Aguardando instalação</h4>
            <p>
              Instale o Agent no ambiente do cliente para descobrir impressoras
              e enviar dados de monitoramento.
            </p>
            <button className="secondary-button">Preparar instalação</button>
          </article>
        </section>
      </main>
    </div>
  )
}

export default App
