import { lazy, Suspense, useEffect, useState } from "react"
import type { FormEvent } from "react"
import "./App.css"
import Dashboard from "./components/Dashboard"

const PrinterTable = lazy(() => import("./components/PrinterTable"))
const AgentMonitor = lazy(() => import("./components/AgentMonitor"))
const ControlCenter = lazy(() => import("./components/ControlCenter"))
const Reports = lazy(() => import("./components/Reports"))
import ThemeToggle from "./components/ThemeToggle"
import { getDashboardPrinters, getMe } from "./services/api"
import type { DashboardPrinter, MeProfile } from "./services/api"

const API_URL = (
  import.meta.env.VITE_API_URL ||
  "https://printflow-api-3uwr.onrender.com"
).replace(/\/$/, "")

type Company = {
  id: number
  uuid: string
  name: string
  document?: string | null
  city?: string | null
  state?: string | null
  plan: string
  default_cost_per_page: number
  default_bw_cost_per_page: number
  default_color_cost_per_page: number
  agent_token: string
  active: boolean
}

type Page = "dashboard" | "printers" | "reports" | "company" | "agents" | "control"

function App() {
  const [authenticated, setAuthenticated] = useState(false)
  const [authReady, setAuthReady] = useState(false)
  const [company, setCompany] = useState<Company | null>(null)
  const [profile, setProfile] = useState<MeProfile | null>(null)
  const initialResetToken = new URLSearchParams(window.location.search).get("reset_token") || ""
  const [mode, setMode] = useState<"login" | "forgot" | "reset">(
    initialResetToken ? "reset" : "login",
  )
  const [resetToken] = useState(initialResetToken)
  const [message, setMessage] = useState("")
  const [messageKind, setMessageKind] = useState<"error" | "success">("error")
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState<Page>("dashboard")
  const [printers, setPrinters] = useState<DashboardPrinter[]>([])
  const [printersLoading, setPrintersLoading] = useState(false)

  async function api(path: string, options: RequestInit = {}) {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...(options.method && options.method !== "GET"
          ? { "X-CSRF-Protection": "1" }
          : {}),
        ...(sessionStorage.getItem("printflow_preview_token")
          ? {
              Authorization: `Bearer ${sessionStorage.getItem("printflow_preview_token")}`,
            }
          : {}),
        ...(options.headers || {}),
      },
    })

    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : Array.isArray(data.detail)
            ? data.detail.map((item: { msg?: string }) => item?.msg || JSON.stringify(item)).join("; ")
            : data.detail ? JSON.stringify(data.detail) : "Erro na operação"
      throw new Error(detail)
    }
    return data
  }

  useEffect(() => {
    Promise.all([api("/api/v1/companies/current"), getMe()])
      .then(([companyData, profileData]) => {
        setCompany(companyData)
        setProfile(profileData)
        setAuthenticated(true)
        if (profileData.role !== "platform_admin") setPage("dashboard")
      })
      .catch(() => {
        setAuthenticated(false)
        setCompany(null)
        setProfile(null)
      })
      .finally(() => setAuthReady(true))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setMessage("")
    setMessageKind("error")
    const form = new FormData(event.currentTarget)

    try {
      if (mode === "forgot") {
        const result = await api("/api/v1/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email: form.get("email") }),
        })
        setMessage(result.message || "Se o e-mail estiver cadastrado, enviaremos as instruções.")
        setMessageKind("success")
        return
      }

      if (mode === "reset") {
        const newPassword = String(form.get("new_password") || "")
        const confirmPassword = String(form.get("confirm_password") || "")
        if (newPassword !== confirmPassword) {
          throw new Error("As senhas informadas não são iguais.")
        }
        await api("/api/v1/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({
            reset_token: resetToken,
            new_password: newPassword,
          }),
        })
        window.history.replaceState({}, "", window.location.pathname)
        setMode("login")
        setMessage("Senha redefinida com sucesso. Faça login com a nova senha.")
        setMessageKind("success")
        return
      }

      await api("/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({
          email: form.get("email"),
          password: form.get("password"),
        }),
      })
      setAuthenticated(true)
      setAuthReady(true)
      const [companyData, profileData] = await Promise.all([
        api("/api/v1/companies/current"),
        getMe(),
      ])
      setCompany(companyData)
      setProfile(profileData)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Falha na autenticação")
      setMessageKind("error")
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
          default_cost_per_page: Number(form.get("default_bw_cost_per_page") || 0),
          default_bw_cost_per_page: Number(form.get("default_bw_cost_per_page") || 0),
          default_color_cost_per_page: Number(form.get("default_color_cost_per_page") || 0),
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
      setPrinters(await getDashboardPrinters())
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Erro ao carregar impressoras")
    } finally {
      setPrintersLoading(false)
    }
  }

  async function regenerateToken() {
    if (!confirm("Gerar um novo token? O token anterior deixará de funcionar.")) return
    const updated = await api("/api/v1/companies/current/regenerate-agent-token", { method: "POST" })
    setCompany(updated)
  }

  function leaveClientPreview() {
    sessionStorage.removeItem(
      "printflow_preview_token",
    )
    sessionStorage.removeItem(
      "printflow_preview_company",
    )
    window.location.assign("/")
  }

  async function logout() {
    if (sessionStorage.getItem("printflow_preview_token")) {
      leaveClientPreview()
      return
    }

    try {
      await api("/api/v1/auth/logout", { method: "POST" })
    } catch {
      // A sessão local deve ser encerrada mesmo se a API já estiver expirada.
    }

    sessionStorage.removeItem("printflow_preview_token")
    sessionStorage.removeItem("printflow_preview_company")
    setAuthenticated(false)
    setCompany(null)
    setProfile(null)
    setPage("dashboard")
  }

  if (!authReady) {
    return (
      <main className="auth-page">
        <ThemeToggle />
        <section className="auth-card">
          <p>Validando sessão segura...</p>
        </section>
      </main>
    )
  }

  if (!authenticated) {
    return (
      <main className="auth-page">
        <ThemeToggle />
        <section className="auth-card auth-card-erp">
          <div className="auth-brand">
            <img className="auth-brand-mark" src="/brand/printflow-mark.svg" alt="Símbolo Printflow" />
            <strong>Printflow</strong>
          </div>
          <div className="auth-product-name">Gestão inteligente de impressão</div>
          <div className="auth-flow-title">
            {mode === "login" && <strong>Boas-vindas</strong>}
            {mode === "forgot" && <strong>Recuperar senha</strong>}
            {mode === "reset" && <strong>Definir nova senha</strong>}
          </div>
          <form onSubmit={authenticate}>
            {mode !== "reset" && (
              <label>
                {mode === "login" ? "Insira seu usuário" : "E-mail"}
                <div className="auth-input-wrap auth-input-user">
                  <input
                    name="email"
                    type="email"
                    placeholder="usuario@empresa.com.br"
                    autoComplete="username"
                    required
                  />
                </div>
              </label>
            )}
            {mode === "login" && (
              <>
                <label>
                  Insira sua senha
                  <div className="auth-input-wrap auth-input-password">
                    <input
                      name="password"
                      type="password"
                      autoComplete="current-password"
                      required
                      minLength={8}
                    />
                  </div>
                </label>
              </>
            )}
            {mode === "forgot" && (
              <p className="auth-helper">
                Informe seu e-mail. Se ele estiver cadastrado, enviaremos um link válido por 15 minutos.
              </p>
            )}
            {mode === "reset" && (
              <>
                <label>
                  Nova senha
                  <div className="auth-input-wrap auth-input-password">
                    <input name="new_password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} />
                  </div>
                </label>
                <label>
                  Confirmar nova senha
                  <div className="auth-input-wrap auth-input-password">
                    <input name="confirm_password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} />
                  </div>
                </label>
              </>
            )}
            <button className="primary" disabled={loading}>
              {loading
                ? "Processando..."
                : mode === "login"
                  ? "Entrar"
                  : mode === "forgot"
                    ? "Enviar instruções"
                    : "Redefinir senha"}
            </button>
            {mode === "login" && (
              <button
                type="button"
                className="auth-link auth-forgot-link"
                onClick={() => {
                  setMode("forgot")
                  setMessage("")
                }}
              >
                Esqueceu sua senha?
              </button>
            )}
            {mode !== "login" && (
              <button
                type="button"
                className="auth-link auth-link-back"
                onClick={() => {
                  setMode("login")
                  setMessage("")
                }}
              >
                Voltar para o login
              </button>
            )}
          </form>
          {message && <div className={`message ${messageKind}`}>{message}</div>}
        </section>
      </main>
    )
  }

  const previewCompany =
    sessionStorage.getItem(
      "printflow_preview_company",
    );
  const isClientPreview = Boolean(
    previewCompany &&
    sessionStorage.getItem(
      "printflow_preview_token",
    ),
  );

  return (
    <div className="shell">
      <ThemeToggle />
      {isClientPreview && (
        <div
          style={{
            position: "fixed",
            top: 12,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 1000,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "9px 14px",
            border: "1px solid #1f9d7c",
            borderRadius: 10,
            background: "#0b2b27",
            color: "#d9fff5",
            boxShadow: "0 10px 30px rgba(0,0,0,.25)",
          }}
        >
          <strong>
            Visualizando como cliente:
            {" "}
            {previewCompany}
          </strong>
          <button
            type="button"
            onClick={leaveClientPreview}
          >
            Voltar ao Control Center
          </button>
        </div>
      )}
      <div className="workspace-topbar">
        <div className="workspace-context">
          <span className="workspace-product">
            PRINTFLOW
          </span>
          <span className="workspace-divider">/</span>
          <strong>
            {company?.name || "Empresa monitorada"}
          </strong>
          <span className="workspace-environment">
            {company?.plan === "pilot" ? "Piloto" : company?.plan || "Produção"}
          </span>
        </div>

        <div className="workspace-user">
          <div className="workspace-user-copy">
            <strong>{profile?.name || "Usuário"}</strong>
            <span>
              {profile?.role === "platform_admin"
                ? "Administrador da plataforma"
                : "Usuário da empresa"}
            </span>
          </div>
          <div className="workspace-avatar">
            {(profile?.name || "U").slice(0, 1).toUpperCase()}
          </div>
        </div>
      </div>

      <aside>
        <div className="brand">
          <img src="/brand/printflow-mark.svg" alt="" aria-hidden="true" />
          <div className="brand-copy">
            <strong>Printflow</strong>
            <span>Operations Platform</span>
          </div>
        </div>
        <nav>
          <small className="nav-section-title">MENU PRINCIPAL</small>
          <button className={page === "dashboard" ? "active" : ""} onClick={() => setPage("dashboard")}><span className="nav-icon">⌂</span>Visão Geral</button>
          {profile?.role === "platform_admin" && (
            <button className={page === "control" ? "active" : ""} onClick={() => setPage("control")}><span className="nav-icon">▦</span>Control Center</button>
          )}
          <button className={page === "company" ? "active" : ""} onClick={() => setPage("company")}><span className="nav-icon">⌘</span>Empresa e Agent</button>
          <button className={page === "printers" ? "active" : ""} onClick={() => { setPage("printers"); void loadPrinters() }}><span className="nav-icon">▣</span>Impressoras</button>
          <button className={page === "reports" ? "active" : ""} onClick={() => setPage("reports")}><span className="nav-icon">≡</span>Relatórios</button>
          <button className={page === "agents" ? "active" : ""} onClick={() => setPage("agents")}><span className="nav-icon">◉</span>Agentes</button>
        </nav>
        <button className="logout" onClick={logout}>Sair</button>
      </aside>

      <main className={`dashboard ${page === "dashboard" ? "dashboard-modern-shell" : ""} ${page === "printers" ? "printers-workspace" : ""} ${page === "reports" ? "reports-workspace" : ""}`}>
        <Suspense fallback={<div className="sap-loading">Carregando módulo...</div>}>
        {page === "control" ? (
          <ControlCenter />
        ) : page === "reports" ? (
          <Reports
            companyName={company?.name || "Empresa monitorada"}
            bwRate={company?.default_bw_cost_per_page || company?.default_cost_per_page || 0}
            colorRate={company?.default_color_cost_per_page || 0}
          />
        ) : page === "printers" ? (
          <section className="printers-workspace-page">
            <header className="printers-workspace-header">
              <div>
                <span>PARQUE DE IMPRESSÃO</span>
                <h1>Impressoras</h1>
                <p>
                  {printersLoading
                    ? "Atualizando equipamentos..."
                    : `${printers.length} equipamento(s) monitorado(s) em ${company?.name || "Empresa monitorada"}.`}
                </p>
              </div>
              <div className="printers-workspace-actions">
                <span className="printers-api-status">● API Online</span>
                <button
                  type="button"
                  onClick={() => void loadPrinters()}
                  disabled={printersLoading}
                >
                  {printersLoading ? "Atualizando..." : "Atualizar"}
                </button>
              </div>
            </header>

            <PrinterTable
              printers={printers}
              defaultCostPerPage={company?.default_bw_cost_per_page || company?.default_cost_per_page || 0}
            />
          </section>
        ) : page === "agents" ? (
          <AgentMonitor agentToken={company?.agent_token || null} onRegenerateToken={regenerateToken} />
        ) : page === "company" ? (
          <>
            <header>
              <div><small>CONFIGURAÇÃO</small><h1>Empresa e Agent</h1></div>
              <span className="online">● API Online</span>
            </header>
            <section className="hero">
              <div>
                <small>Printflow · AMBIENTE DO CLIENTE</small>
                <h2>{company?.name || "Carregando empresa..."}</h2>
                <p>Dados corporativos, tarifa padrão e vínculo seguro do Agent.</p>
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
                    <div className="row">
                      <label>
                        Tarifa P&B por página (R$)
                        <input
                          name="default_bw_cost_per_page"
                          type="number"
                          min="0"
                          max="100"
                          step="0.0001"
                          defaultValue={Number(company.default_bw_cost_per_page || company.default_cost_per_page || 0).toFixed(4)}
                        />
                      </label>
                      <label>
                        Tarifa colorida por página (R$)
                        <input
                          name="default_color_cost_per_page"
                          type="number"
                          min="0"
                          max="100"
                          step="0.0001"
                          defaultValue={Number(company.default_color_cost_per_page || 0).toFixed(4)}
                        />
                      </label>
                    </div>
                    <small>Tarifas contratuais usadas nos relatórios conforme o tipo de contador disponível.</small>
                    <button className="primary">Salvar empresa</button>
                  </form>
                </article>
                <article className="panel">
                  <h3>Token do Agent (43 caracteres)</h3>
                  <p>Use somente este token para vincular o Agent à empresa. Não copie o token de sessão/login.</p>
                  <code className="token-box">{company.agent_token}</code>
                  <div className="row-actions">
                    <button onClick={() => navigator.clipboard.writeText(company.agent_token)}>Copiar</button>
                    <button onClick={regenerateToken}>Gerar novo</button>
                  </div>
                  <div className="tariff-box">
                    <strong>Tarifas contratuais</strong>
                    <span>P&B: R$ {Number(company.default_bw_cost_per_page || company.default_cost_per_page || 0).toFixed(4).replace(".", ",")} por página</span>
                    <span>Cor: R$ {Number(company.default_color_cost_per_page || 0).toFixed(4).replace(".", ",")} por página</span>
                  </div>
                </article>
              </section>
            )}
            {message && <div className="message">{message}</div>}
          </>
        ) : (
          <Dashboard companyName={company?.name || "Empresa monitorada"} onOpenPrinters={() => { setPage("printers"); void loadPrinters() }} />
        )}
        </Suspense>
      </main>
    </div>
  )
}

export default App
