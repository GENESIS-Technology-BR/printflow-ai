import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

const API_URL = (
  import.meta.env.VITE_API_URL || "https://printflow-api-genesis.onrender.com"
).replace(/\/$/, "");

type PartnerCompany = {
  id: number;
  name: string;
  partner_id: number | null;
  customer_portal_enabled: boolean;
  active: boolean;
};

type FleetAlert = { id: number; title: string; severity: string; status: string; description: string };

type FleetPrinter = { id: number | null; name: string; ip: string | null; status: string; model: string | null; sector_name: string | null };

type PortfolioSummary = { companies: number; active_printers: number; online_printers: number; offline_printers: number };

type CompanyOverview = {
  company_id: number;
  total_active_printers: number;
  online_printers: number;
  offline_printers: number;
  agent_status: string | null;
};

type PartnerDirectoryEntry = { id: number; name: string; active: boolean };
type PartnerPreview = { partner: { id: number; name: string }; companies: { id: number; name: string; customer_portal_enabled: boolean }[]; preview_only: boolean };

type PartnerContext = {
  platform_admin: boolean;
  partners: { id: number; name: string; role: string }[];
};

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("printflow_preview_token");
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.method && init.method !== "GET" ? { "X-CSRF-Protection": "1" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers || {}),
    },
  });
  if (!response.ok) throw new Error(response.status === 403 ? "Acesso não autorizado" : "Não foi possível carregar a carteira");
  return response.json() as Promise<T>;
}

export default function PartnerPortfolio() {
  const [context, setContext] = useState<PartnerContext | null>(null);
  const [companies, setCompanies] = useState<PartnerCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [overviews, setOverviews] = useState<Record<number, CompanyOverview>>({});
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [selectedCompany, setSelectedCompany] = useState<PartnerCompany | null>(null);
  const [fleet, setFleet] = useState<FleetPrinter[]>([]);
  const [alerts, setAlerts] = useState<FleetAlert[]>([]);
  const [fleetLoading, setFleetLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [directory, setDirectory] = useState<PartnerDirectoryEntry[]>([]);
  const [preview, setPreview] = useState<PartnerPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [newPartnerName, setNewPartnerName] = useState("");
  const [creatingPartner, setCreatingPartner] = useState(false);
  const [changingPartnerId, setChangingPartnerId] = useState<number | null>(null);
  const [memberPartnerId, setMemberPartnerId] = useState("");
  const [memberUserId, setMemberUserId] = useState("");
  const [memberRole, setMemberRole] = useState("partner_admin");
  const [addingMember, setAddingMember] = useState(false);
  const [notice, setNotice] = useState("");

  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [ctx, list] = await Promise.all([
        api<PartnerContext>("/partners/me"),
        api<PartnerCompany[]>("/partners/my-companies"),
      ]);
      setContext(ctx);
      setCompanies(list);
      if (ctx.platform_admin) {
        setDirectory(await api<PartnerDirectoryEntry[]>("/partners/directory"));
      } else {
        setDirectory([]);
        setPreview(null);
      }
      const totals = await api<PortfolioSummary>("/partners/portfolio-summary");
      setSummary(totals);
      const overviewResults = await Promise.allSettled(
        list.map((company) => api<CompanyOverview>(`/partners/companies/${company.id}/overview`))
      );
      const scoped: Record<number, CompanyOverview> = {};
      overviewResults.forEach((result) => {
        if (result.status === "fulfilled") scoped[result.value.company_id] = result.value;
      });
      setOverviews(scoped);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao consultar parceiros");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void reload(); }, [reload]);

  async function createPartner(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newPartnerName.trim();
    if (name.length < 2 || name.length > 180) return;
    setCreatingPartner(true);
    setError("");
    try {
      await api("/partners/directory", { method: "POST", body: JSON.stringify({ name }) });
      setNewPartnerName("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível cadastrar o parceiro");
    } finally {
      setCreatingPartner(false);
    }
  }

  async function changePartnerStatus(partner: PartnerDirectoryEntry) {
    const active = !partner.active;
    if (!window.confirm(`Confirma ${active ? "reativar" : "suspender"} ${partner.name}? ${active ? "O acesso dos membros será restaurado." : "Os membros perderão acesso à carteira imediatamente."}`)) return;
    setChangingPartnerId(partner.id);
    setError("");
    try {
      await api(`/partners/directory/${partner.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ active }),
      });
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível alterar o parceiro");
    } finally {
      setChangingPartnerId(null);
    }
  }

  async function addPartnerMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const partnerId = Number(memberPartnerId);
    const userId = Number(memberUserId);
    if (!Number.isSafeInteger(partnerId) || partnerId <= 0 || !Number.isSafeInteger(userId) || userId <= 0) return;
    setAddingMember(true);
    setError("");
    setNotice("");
    try {
      await api(`/partners/directory/${partnerId}/members`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId, role: memberRole }),
      });
      setMemberUserId("");
      setNotice("Usuário existente vinculado ao parceiro com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível vincular o usuário");
    } finally {
      setAddingMember(false);
    }
  }

  async function openPartnerPreview(partnerId: number) {
    setPreview(null);
    if (!partnerId) return;
    setPreviewLoading(true);
    setError("");
    try {
      setPreview(await api<PartnerPreview>(`/partners/directory/${partnerId}/preview-companies`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao consultar pré-visualização");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function openFleet(company: PartnerCompany) {
    setSelectedCompany(company);
    setFleet([]);
    setAlerts([]);
    setFleetLoading(true);
    setError("");
    try {
      const [printers, companyAlerts] = await Promise.all([
        api<FleetPrinter[]>(`/partners/companies/${company.id}/printers`),
        api<FleetAlert[]>(`/partners/companies/${company.id}/alerts`),
      ]);
      setFleet(printers);
      setAlerts(companyAlerts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao consultar impressoras");
    } finally {
      setFleetLoading(false);
    }
  }

  async function setPortal(company: PartnerCompany) {
    const allowed = context?.platform_admin || context?.partners.some(
      (p) => p.id === company.partner_id && p.role === "partner_admin"
    );
    if (!allowed) return;
    const nextEnabled = !company.customer_portal_enabled;
    const action = nextEnabled ? "habilitar" : "desabilitar";
    if (!window.confirm(`Confirma ${action} o portal de ${company.name}? Essa alteração afeta o acesso dos usuários dessa empresa.`)) return;
    setBusyId(company.id);
    setError("");
    try {
      await api(`/partners/companies/${company.id}/customer-portal`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: nextEnabled }),
      });
      setCompanies((previous) => previous.map((item) =>
        item.id === company.id
          ? { ...item, customer_portal_enabled: nextEnabled }
          : item
      ));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao alterar portal");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="partner-portfolio">
      <header>
        <div>
          <small>GESTÃO DE CARTEIRA</small>
          <h1>Empresas atendidas</h1>
          <p>Gerencie o acesso opcional dos seus clientes ao TALVOA.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading}>
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </header>
      {error && <p role="alert">{error}</p>}
      {context?.platform_admin && (
        <div className="panel">
          <h2>Administração TALVOA — parceiros</h2>
          <form onSubmit={(event) => void createPartner(event)}>
            <label htmlFor="new-partner-name">Nome do parceiro</label>{" "}
            <input id="new-partner-name" type="text" minLength={2} maxLength={180} required
              value={newPartnerName} onChange={(event) => setNewPartnerName(event.target.value)}
              placeholder="Ex.: SupriTech" />
            <button type="submit" disabled={creatingPartner || newPartnerName.trim().length < 2}>
              {creatingPartner ? "Cadastrando..." : "Cadastrar parceiro"}
            </button>
          </form>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr><th scope="col">Parceiro</th><th scope="col">Situação</th><th scope="col">Ação</th></tr></thead>
            <tbody>{directory.map((partner) => (
              <tr key={partner.id}>
                <td>{partner.name}</td>
                <td>{partner.active ? "Ativo" : "Suspenso"}</td>
                <td><button type="button" disabled={changingPartnerId !== null}
                  onClick={() => void changePartnerStatus(partner)}>
                  {changingPartnerId === partner.id ? "Salvando..." : partner.active ? "Suspender" : "Reativar"}
                </button></td>
              </tr>
            ))}</tbody>
          </table>
          {directory.length === 0 && <p>Nenhum parceiro cadastrado.</p>}
          <h2>Vincular usuário existente</h2>
          <p>Associe um usuário já cadastrado à carteira do parceiro. Administradores da plataforma não podem ser vinculados.</p>
          <form onSubmit={(event) => void addPartnerMember(event)}>
            <label htmlFor="member-partner">Parceiro</label>{" "}
            <select id="member-partner" required value={memberPartnerId}
              onChange={(event) => setMemberPartnerId(event.target.value)}>
              <option value="">Selecione</option>
              {directory.filter((partner) => partner.active).map((partner) => (
                <option key={partner.id} value={partner.id}>{partner.name}</option>
              ))}
            </select>{" "}
            <label htmlFor="member-user-id">ID do usuário existente</label>{" "}
            <input id="member-user-id" type="number" min="1" step="1" required
              value={memberUserId} onChange={(event) => setMemberUserId(event.target.value)} />{" "}
            <label htmlFor="member-role">Permissão</label>{" "}
            <select id="member-role" value={memberRole} onChange={(event) => setMemberRole(event.target.value)}>
              <option value="partner_admin">Administrador</option>
              <option value="partner_operator">Operador</option>
              <option value="partner_viewer">Consulta</option>
            </select>{" "}
            <button type="submit" disabled={addingMember || !memberPartnerId || !memberUserId}>
              {addingMember ? "Vinculando..." : "Vincular usuário"}
            </button>
          </form>
          {notice && <p role="status">{notice}</p>}
          <h2>Pré-visualização de parceiro</h2>
          <p>Consulta administrativa somente leitura. Não altera sua identidade nem as permissões dos parceiros.</p>
          <label htmlFor="partner-preview-select">Parceiro</label>{" "}
          <select id="partner-preview-select" defaultValue="" onChange={(event) => void openPartnerPreview(Number(event.target.value))}>
            <option value="">Selecione um parceiro</option>
            {directory.filter((p) => p.active).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          {previewLoading && <p>Consultando carteira...</p>}
          {preview && <div>
            <strong>{preview.partner.name}: {preview.companies.length} cliente(s)</strong>
            {preview.companies.map((company) => <p key={company.id}>{company.name} — Portal: {company.customer_portal_enabled ? "habilitado" : "desabilitado"}</p>)}
            {preview.companies.length === 0 && <p>Nenhum cliente vinculado.</p>}
          </div>}
        </div>
      )}
      {loading ? <p>Carregando carteira...</p> : (
        <>
          <div className="grid">
            <article className="panel"><strong>Empresas</strong><h2>{summary?.companies ?? companies.length}</h2></article>
            <article className="panel"><strong>Impressoras ativas</strong><h2>{summary?.active_printers ?? "—"}</h2></article>
            <article className="panel"><strong>Online</strong><h2>{summary?.online_printers ?? "—"}</h2></article>
            <article className="panel"><strong>Offline</strong><h2>{summary?.offline_printers ?? "—"}</h2></article>
          </div>
          <div className="panel">
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr><th scope="col">Empresa</th><th scope="col">Impressoras</th><th scope="col">Online</th><th scope="col">Offline</th><th scope="col">Portal do cliente</th><th scope="col">Ação</th></tr></thead>
              <tbody>
                {companies.map((company) => {
                  const canManage = context?.platform_admin || context?.partners.some(
                    (p) => p.id === company.partner_id && p.role === "partner_admin"
                  );
                  return (
                    <tr key={company.id}>
                      <td><button type="button" onClick={() => void openFleet(company)}>{company.name}</button></td>
                      <td>{overviews[company.id]?.total_active_printers ?? "—"}</td>
                      <td>{overviews[company.id]?.online_printers ?? "—"}</td>
                      <td>{overviews[company.id]?.offline_printers ?? "—"}</td>
                      <td>{company.customer_portal_enabled ? "Habilitado" : "Desabilitado"}</td>
                      <td>
                        {canManage ? (
                          <button
                            type="button"
                            disabled={busyId !== null}
                            onClick={() => void setPortal(company)}
                          >
                            {busyId === company.id ? "Salvando..." : company.customer_portal_enabled ? "Desabilitar" : "Habilitar"}
                          </button>
                        ) : "Somente consulta"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {companies.length === 0 && <p>Nenhuma empresa vinculada ao parceiro.</p>}
          </div>
        </>
      )}
      {selectedCompany && (
        <div className="panel">
          <header>
            <div><small>INVENTÁRIO POR EMPRESA</small><h2>{selectedCompany.name}</h2></div>
            <button type="button" onClick={() => setSelectedCompany(null)}>Fechar</button>
          </header>
          {fleetLoading ? <p>Carregando impressoras...</p> : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr><th>Nome</th><th>IP</th><th>Modelo</th><th>Setor</th><th>Status</th></tr></thead>
              <tbody>{fleet.map((printer) => (
                <tr key={printer.id ?? printer.ip ?? printer.name}>
                  <td>{printer.name}</td><td>{printer.ip ?? "—"}</td>
                  <td>{printer.model ?? "—"}</td><td>{printer.sector_name ?? "—"}</td><td>{printer.status}</td>
                </tr>
              ))}</tbody>
            </table>
          )}
          {!fleetLoading && fleet.length === 0 && <p>Nenhuma impressora cadastrada.</p>}
          {!fleetLoading && <div><h3>Alertas recentes ({alerts.length})</h3>
            {alerts.filter((item) => item.status !== "resolved").slice(0, 10).map((item) => (
              <p key={item.id}><strong>{item.severity.toUpperCase()}</strong> — {item.title}: {item.description}</p>
            ))}
          </div>}
        </div>
      )}
    </section>
  );
}
