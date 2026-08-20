import { useEffect, useState } from "react"
import type { FormEvent } from "react"
import "./App.css"
import Dashboard from "./components/Dashboard"
import PrinterTable from "./components/PrinterTable"
import { getDashboardPrinters } from "./services/api"
import type { DashboardPrinter } from "./services/api"

const API_URL = (
  import.meta.env.VITE_API_URL ||
  "https://printflow-api-genesis.onrender.com"
).replace(/\/$/, "")

type Company = {
  id: number
  uuid: string
  name: string
  document?: string | null
  city?: string | null
  state?: string | null
  plan: string
  agent_token: string
  active: boolean
}

type AuthResponse = {
  access_token: string
  user_name: string
  company_name: string
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("printflow_token") || "")
  const [company, setCompany] = useState<Company | null>(null)
  const [mode, setMode] = useState<"login" | "register">("login")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState<"dashboard" | "printers" | "company" | "agents">("dashboard")
  const [printers, setPrinters] = useState<DashboardPrinter[]>([])
  const [printersLoading, setPrintersLoading] = useState(false)

  async function api(path: string, options: RequestInit = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail
                .map((item: { msg?: string }) => item?.msg || JSON.stringify(item))
                .join("; ")
            : data.detail
              ? JSON.stringify(data.detail)
              : "Erro na operação"

      throw new Error(detail)
    }
    return data
  }

  useEffect(() => {
    if (!token) return
    api("/api/v1/companies/current")
      .then(setCompany)
      .catch(() => logout())
  // A função api usa o token atual e é recriada junto com este efeito.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setMessage("")
    const form = new FormData(event.currentTarget)

    const body = mode === "login"
      ? {
          email: form.get("email"),
          password: form.get("password"),
        }
      : {
          user_name: form.get("user_name"),
          company_name: form.get("company_name"),
          email: form.get("email"),
          password: form.get("password"),
        }

    try {
      const result: AuthResponse = await api(`/api/v1/auth/${mode}`, {
        method: "POST",
        body: JSON.stringify(body),
      })
      localStorage.setItem("printflow_token", result.access_token)
      setToken(result.access_token)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha na autenticação")
    } finally {
      setLoading(false)
    }
  }

  async function updateCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      const updated = await api("/api/v1/companies/current", {
        method: "PATCH",
        body: JSON.stringify({
          name: form.get("name"),
          document: form.get("document") || null,
          city: form.get("city") || null,
          state: form.get("state") || null,
        }),
      })
      setCompany(updated)
      setMessage("Empresa atualizada com sucesso.")
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Erro ao salvar")
    }
  }

  async function loadPrinters() {
    setPrintersLoading(true)
    setMessage("")

    try {
      const result = await getDashboardPrinters()
      setPrinters(result)
    } catch (error) {
      setMessage(
        error instanceof Error
          ? error.message
          : "Erro ao carregar impressoras"
      )
    } finally {
      setPrintersLoading(false)
    }
  }

  async function regenerateToken() {
    if (!confirm("Gerar um novo token? O token anterior deixará de funcionar.")) return
    const updated = await api("/api/v1/companies/current/regenerate-agent-token", {
      method: "POST",
    })
    setCompany(updated)
  }

  function logout() {
    localStorage.removeItem("printflow_token")
    setToken("")
    setCompany(null)
  }

  if (!token) {
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div className="logo">P</div>
          <h1>PRINTFLOW AI</h1>
          <p>Gestão inteligente de impressão</p>

          <div className="tabs">
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
              Entrar
            </button>
            <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>
              Criar conta
            </button>
          </div>

          <form onSubmit={authenticate}>
            {mode === "register" && (
              <>
                <label>Seu nome<input name="user_name" required minLength={3} /></label>
                <label>Empresa<input name="company_name" required minLength={2} /></label>
              </>
            )}
            <label>E-mail<input name="email" type="email" required /></label>
            <label>Senha<input name="password" type="password" required minLength={8} /></label>
            <button className="primary" disabled={loading}>
              {loading ? "Processando..." : mode === "login" ? "Entrar" : "Criar conta e empresa"}
            </button>
          </form>
          {message && <div className="message error">{message}</div>}
        </section>
      </main>
    )
  }

  return (
    <div className="shell">
      <aside>
        <div className="brand"><span>P</span><strong>PRINTFLOW AI</strong></div>
        <nav>
          <button
          className={page === "dashboard" ? "active" : ""}
          onClick={() => setPage("dashboard")}
        >
          Visão Geral
        </button>
          <button
          className={page === "company" ? "active" : ""}
          onClick={() => setPage("company")}
        >
          Empresa e Agent
        </button>
          <button className={page === "printers" ? "active" : ""} onClick={() => { setPage("printers"); void loadPrinters() }}>Impressoras</button>
          <button className={page === "agents" ? "active" : ""} onClick={() => setPage("agents")}>Agentes</button>
        </nav>
        <button className="logout" onClick={logout}>Sair</button>
      </aside>

      <main className="dashboard">
      {page === "printers" ? (
        <>
          <header>
            <div>
              <small>MONITORAMENTO</small>
              <h1>Impressoras</h1>
            </div>
            <span className="online">● API Online</span>
          </header>

          <section className="hero">
            <div>
              <small>PRINTFLOW AI · PARQUE MONITORADO</small>
              <h2>Impressoras da empresa</h2>
              <p>
                {printersLoading
                  ? "Carregando equipamentos..."
                  : `${printers.length} equipamento(s) encontrado(s).`}
              </p>
            </div>
          </section>

          <section className="content-grid">
            <article
              className="panel"
              style={{ gridColumn: "1 / -1" }}
            >
              <div className="actions">
                <button
                  type="button"
                  onClick={() => void loadPrinters()}
                  disabled={printersLoading}
                >
                  {printersLoading ? "Atualizando..." : "Atualizar lista"}
                </button>
              </div>

              <PrinterTable printers={printers} />
            </article>
          </section>
        </>
      ) : page === "agents" ? (
        <>
          <header>
            <div>
              <small>COLETA E DESCOBERTA</small>
              <h1>Agent PRINTFLOW</h1>
            </div>
            <span className="online">● API Online</span>
          </header>

          <section className="hero">
            <div>
              <small>PRINTFLOW AI · AGENT</small>
              <h2>Conectar a rede da empresa</h2>
              <p>
                Configure o Agent para localizar impressoras e enviar os
                dados ao PRINTFLOW.
              </p>
            </div>
          </section>

          <section className="content-grid">
            <article className="panel">
              <h3>Token do Agent (43 caracteres)</h3>
              <p>
                Copie somente este token. Não use o token de sessão/login do navegador.
              </p>

              <code>{company?.agent_token || "Token não disponível"}</code>

              <div className="actions">
                <button
                  type="button"
                  onClick={() =>
                    company?.agent_token &&
                    navigator.clipboard.writeText(company.agent_token)
                  }
                >
                  Copiar token
                </button>

                <button
                  type="button"
                  className="danger"
                  onClick={regenerateToken}
                >
                  Gerar novo
                </button>
              </div>
            </article>

            <article className="panel">
              <h3>Procedimento do Agent</h3>

              <div className="status-box">
                <strong>1. Instalar</strong>
                <span>
                  Executar o Agent em um computador Windows da rede do
                  cliente.
                </span>
              </div>

              <div className="status-box">
                <strong>2. Configurar</strong>
                <span>
                  Informar a URL da API e o token desta empresa.
                </span>
              </div>

              <div className="status-box">
                <strong>3. Descobrir</strong>
                <span>
                  Localizar a HP 10.2.0.124 e demais impressoras via SNMP.
                </span>
              </div>

              <div className="status-box">
                <strong>4. Enviar</strong>
                <span>
                  Publicar modelo, serial, IP, status e contadores na API.
                </span>
              </div>
            </article>
          </section>
        </>
      ) : page === "company" ? (
        <>
        <header>
          <div><small>SPRINT COMERCIAL</small><h1>Empresa e Agent</h1></div>
          <span className="online">● API Online</span>
        </header>

        <section className="hero">
          <div>
            <small>PRINTFLOW AI · PACOTE 001</small>
            <h2>{company?.name || "Carregando empresa..."}</h2>
            <p>Conta protegida por JWT e ambiente isolado por empresa.</p>
          </div>
          <div className="plan">Plano {company?.plan || "pilot"}</div>
        </section>

        {company && (
          <section className="grid">
            <article className="panel">
              <h3>Dados da empresa</h3>
              <form onSubmit={updateCompany}>
                <label>Nome<input name="name" defaultValue={company.name} required /></label>
                <label>CNPJ/Documento<input name="document" defaultValue={company.document || ""} /></label>
                <div className="row">
                  <label>Cidade<input name="city" defaultValue={company.city || ""} /></label>
                  <label>UF<input name="state" maxLength={2} defaultValue={company.state || ""} /></label>
                </div>
                <button className="primary">Salvar empresa</button>
              </form>
            </article>

            <article className="panel">
              <h3>Token do Agent (43 caracteres)</h3>
              <p>Use somente este token para vincular o Agent à empresa. Não copie o token de sessão/login.</p>
              <code>{company.agent_token}</code>
              <div className="actions">
                <button onClick={() => navigator.clipboard.writeText(company.agent_token)}>Copiar</button>
                <button className="danger" onClick={regenerateToken}>Gerar novo</button>
              </div>
              <div className="status-box">
                <strong>Próxima etapa</strong>
                <span>Executar Agent na rede e descobrir a HP 10.2.0.124.</span>
              </div>
            </article>
          </section>
        )}
        {message && <div className="message success">{message}</div>}
              </>
                ) : (
            <Dashboard />
          )}
    </main>
    </div>
  )
}

export default App
