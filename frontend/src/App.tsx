import { useEffect, useState } from "react"
import "./App.css"

type Company = {
  id: number
  uuid: string
  name: string
  active: boolean
  created_at: string
}

type Printer = {
  id: number
  uuid: string
  ip: string
  name: string
  manufacturer?: string | null
  model?: string | null
  status: string
  source: string
  page_count?: number | null
  active: boolean
  last_seen: string
  created_at: string
}

const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "")

function App() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [printers, setPrinters] = useState<Printer[]>([])
  const [apiOnline, setApiOnline] = useState(false)
  const [loading, setLoading] = useState(true)

  async function loadDashboard() {
    try {
      const [healthResponse, companiesResponse, printersResponse] = await Promise.all([
        fetch(`${API_URL}/health`),
        fetch(`${API_URL}/api/v1/companies`),
        fetch(`${API_URL}/api/v1/printers`),
      ])

      setApiOnline(healthResponse.ok)

      if (companiesResponse.ok) {
        setCompanies(await companiesResponse.json())
      }

      if (printersResponse.ok) {
        setPrinters(await printersResponse.json())
      }
    } catch (error) {
      console.error("Falha ao conectar com a API:", error)
      setApiOnline(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
    const interval = window.setInterval(loadDashboard, 15000)
    return () => window.clearInterval(interval)
  }, [])

  const onlinePrinters = printers.filter((printer) => printer.status === "online").length
  const offlinePrinters = printers.length - onlinePrinters

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
            <span className="hero-badge">PRINTFLOW AI · v0.3</span>
            <h2>Gestão inteligente do ambiente de impressão</h2>
            <p>Dados reais enviados pelo PRINTFLOW Agent e atualizados automaticamente.</p>
          </div>
          <div className={`system-status ${apiOnline ? "online" : "offline"}`}>
            <span />
            {apiOnline ? "Sistema operacional" : "API indisponível"}
          </div>
        </section>

        <section className="metrics">
          <article className="metric-card">
            <span className="metric-icon">▣</span>
            <div><p>Empresas</p><strong>{loading ? "..." : companies.length}</strong><small>cadastradas</small></div>
          </article>

          <article className="metric-card">
            <span className="metric-icon">▧</span>
            <div><p>Impressoras</p><strong>{loading ? "..." : printers.length}</strong><small>{onlinePrinters} online</small></div>
          </article>

          <article className="metric-card">
            <span className="metric-icon">◉</span>
            <div><p>Online</p><strong>{onlinePrinters}</strong><small>respondendo</small></div>
          </article>

          <article className="metric-card">
            <span className="metric-icon">△</span>
            <div><p>Offline</p><strong>{offlinePrinters}</strong><small>sem comunicação</small></div>
          </article>
        </section>

        <section className="dashboard-grid">
          <article className="panel companies-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">Inventário real</p>
                <h3>Impressoras monitoradas</h3>
              </div>
              <button className="primary-button" onClick={loadDashboard}>Atualizar</button>
            </div>

            {loading ? (
              <div className="empty-state">Carregando impressoras...</div>
            ) : printers.length === 0 ? (
              <div className="empty-state">
                Nenhuma impressora recebida. Execute o PRINTFLOW Agent.
              </div>
            ) : (
              <div className="company-list">
                {printers.map((printer) => (
                  <div className="company-row" key={printer.uuid}>
                    <div className="company-logo">
                      {(printer.manufacturer || "PR").slice(0, 2).toUpperCase()}
                    </div>
                    <div className="company-info">
                      <strong>{printer.name}</strong>
                      <span>
                        {printer.ip} · {printer.model || "Modelo não identificado"}
                      </span>
                    </div>
                    <span className={printer.status === "online" ? "badge-active" : "badge-inactive"}>
                      {printer.status === "online" ? "Online" : "Offline"}
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
            <h4>{printers.length > 0 ? "Agent comunicando" : "Aguardando execução"}</h4>
            <p>
              {printers.length > 0
                ? `Últimos dados recebidos de ${printers.length} impressora(s).`
                : "Execute o Agent no Windows para registrar a HP 10.2.0.124."}
            </p>
            <button className="secondary-button" onClick={loadDashboard}>Sincronizar agora</button>
          </article>
        </section>
      </main>
    </div>
  )
}

export default App
