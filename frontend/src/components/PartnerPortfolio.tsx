import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

const API_URL = (
  import.meta.env.VITE_API_URL || "https://printflow-api-genesis.onrender.com"
).replace(/\/$/, "").replace(/^\/$/, "");

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
type PartnerMember = { id: number; user_id: number; name: string; email: string; role: string; active: boolean };
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
  const [showPartnerAdmin, setShowPartnerAdmin] = useState(false);
  const [showClientForm, setShowClientForm] = useState(false);
  const [companySearch, setCompanySearch] = useState("");
  const [clientPartnerId, setClientPartnerId] = useState("");
  const [clientName, setClientName] = useState("");
  const [clientResponsible, setClientResponsible] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  const [clientCreating, setClientCreating] = useState(false);
  const [createdClient, setCreatedClient] = useState<{ company_name: string; email: string; temporary_password: string } | null>(null);
  const [companyStatusFilter, setCompanyStatusFilter] = useState<"all" | "attention" | "online">("all");
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
  const [newUserPartnerId, setNewUserPartnerId] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [creatingUser, setCreatingUser] = useState(false);
  const [viewMembersPartnerId, setViewMembersPartnerId] = useState("");
  const [partnerMembers, setPartnerMembers] = useState<PartnerMember[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [changingMemberId, setChangingMemberId] = useState<number | null>(null);

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

  async function changeMemberStatus(member: PartnerMember) {
    const partnerId = Number(viewMembersPartnerId);
    if (!partnerId || !window.confirm(`Confirma ${member.active ? "revogar" : "restaurar"} o acesso de ${member.name} a este parceiro?`)) return;
    setChangingMemberId(member.id);
    setError("");
    try {
      await api(`/partners/directory/${partnerId}/members/${member.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ active: !member.active }),
      });
      await loadPartnerMembers(String(partnerId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível alterar o acesso");
    } finally {
      setChangingMemberId(null);
    }
  }

  async function loadPartnerMembers(partnerId: string) {
    setViewMembersPartnerId(partnerId);
    setPartnerMembers([]);
    if (!partnerId) return;
    setMembersLoading(true);
    setError("");
    try {
      setPartnerMembers(await api<PartnerMember[]>(`/partners/directory/${Number(partnerId)}/members`));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível consultar os usuários");
    } finally {
      setMembersLoading(false);
    }
  }

  async function createPartnerUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const partnerId = Number(newUserPartnerId);
    if (!Number.isSafeInteger(partnerId) || partnerId <= 0 || newUserPassword.length < 12) return;
    setCreatingUser(true);
    setError("");
    setNotice("");
    try {
      await api(`/partners/directory/${partnerId}/users`, {
        method: "POST",
        body: JSON.stringify({
          name: newUserName.trim(),
          email: newUserEmail.trim(),
          password: newUserPassword,
          role: "partner_admin",
        }),
      });
      setNewUserName("");
      setNewUserEmail("");
      setNewUserPassword("");
      setNotice("Administrador do parceiro cadastrado com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível cadastrar o usuário");
    } finally {
      setCreatingUser(false);
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

  async function createClient(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const partnerId = Number(clientPartnerId);
    if (!Number.isSafeInteger(partnerId) || partnerId <= 0) return;
    setClientCreating(true);
    setCreatedClient(null);
    setError("");
    try {
      const result = await api<{ company_name: string; email: string; temporary_password: string }>("/partners/clients", {
        method: "POST",
        body: JSON.stringify({
          partner_id: partnerId,
          company_name: clientName.trim(),
          responsible_name: clientResponsible.trim(),
          email: clientEmail.trim(),
        }),
      });
      setCreatedClient(result);
      setClientName("");
      setClientResponsible("");
      setClientEmail("");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível cadastrar o cliente");
    } finally {
      setClientCreating(false);
    }
  }

  const openAlertCount = alerts.filter((alert) => alert.status !== "resolved").length;
  const companiesNeedingAttention = companies.filter((company) => (overviews[company.id]?.offline_printers ?? 0) > 0).length;
  const visibleCompanies = companies.filter((company) => {
    const overview = overviews[company.id];
    if (!company.name.toLocaleLowerCase("pt-BR").includes(companySearch.trim().toLocaleLowerCase("pt-BR"))) return false;
    if (companyStatusFilter === "attention") return (overview?.offline_printers ?? 0) > 0;
    if (companyStatusFilter === "online") return overview !== undefined && overview.offline_printers === 0;
    return true;
  });

  return (
    <section className="partner-portfolio">
      <header>
        <div>
          <small>GESTÃO DE CARTEIRA</small>
          <h1>{context?.platform_admin ? "Carteira de empresas" : "Central de Gestão de Clientes"}</h1>
          <p>Monitore os clientes da carteira, acompanhe a disponibilidade das impressoras e consulte alertas por empresa.</p>
        </div>
        <button type="button" onClick={() => void reload()} disabled={loading}>
          {loading ? "Atualizando..." : "Atualizar"}
        </button>
      </header>
      {error && <p role="alert">{error}</p>}
      {context?.platform_admin && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <button type="button" aria-expanded={showPartnerAdmin} onClick={() => setShowPartnerAdmin((value) => !value)}>
            {showPartnerAdmin ? "Ocultar administração de parceiros" : "Gerenciar parceiros e acessos"}
          </button>
          {showPartnerAdmin && <div>
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
          <h2>Usuários do parceiro</h2>
          <label htmlFor="members-partner-select">Parceiro</label>{" "}
          <select id="members-partner-select" value={viewMembersPartnerId}
            onChange={(event) => void loadPartnerMembers(event.target.value)}>
            <option value="">Selecione</option>
            {directory.map((partner) => <option key={partner.id} value={partner.id}>{partner.name}</option>)}
          </select>
          {membersLoading ? <p>Carregando usuários...</p> : viewMembersPartnerId && (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr><th scope="col">Nome</th><th scope="col">E-mail</th><th scope="col">Perfil</th><th scope="col">Situação</th><th scope="col">Ação</th></tr></thead>
              <tbody>{partnerMembers.map((member) => (
                <tr key={member.id}><td>{member.name}</td><td>{member.email}</td>
                  <td>{member.role}</td><td>{member.active ? "Ativo" : "Inativo"}</td>
                  <td><button type="button" disabled={changingMemberId !== null}
                    onClick={() => void changeMemberStatus(member)}>
                    {changingMemberId === member.id ? "Salvando..." : member.active ? "Revogar" : "Restaurar"}
                  </button></td></tr>
              ))}</tbody>
            </table>
          )}
          {!membersLoading && viewMembersPartnerId && partnerMembers.length === 0 && <p>Nenhum usuário vinculado.</p>}
          <h2>Cadastrar administrador do parceiro</h2>
          <p>Crie uma conta individual para a revenda. A senha não será exibida após o cadastro.</p>
          <form onSubmit={(event) => void createPartnerUser(event)}>
            <label htmlFor="new-user-partner">Parceiro</label>{" "}
            <select id="new-user-partner" required value={newUserPartnerId}
              onChange={(event) => setNewUserPartnerId(event.target.value)}>
              <option value="">Selecione</option>
              {directory.filter((partner) => partner.active).map((partner) => (
                <option key={partner.id} value={partner.id}>{partner.name}</option>
              ))}
            </select>{" "}
            <label htmlFor="new-user-name">Nome</label>{" "}
            <input id="new-user-name" required minLength={3} maxLength={120} value={newUserName}
              onChange={(event) => setNewUserName(event.target.value)} />{" "}
            <label htmlFor="new-user-email">E-mail</label>{" "}
            <input id="new-user-email" required type="email" value={newUserEmail}
              onChange={(event) => setNewUserEmail(event.target.value)} />{" "}
            <label htmlFor="new-user-password">Senha inicial (mínimo 12 caracteres)</label>{" "}
            <input id="new-user-password" required type="password" minLength={12} maxLength={128}
              autoComplete="new-password" value={newUserPassword}
              onChange={(event) => setNewUserPassword(event.target.value)} />{" "}
            <button type="submit" disabled={creatingUser || !newUserPartnerId || newUserPassword.length < 12}>
              {creatingUser ? "Cadastrando..." : "Criar administrador"}
            </button>
          </form>
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
          </div>}
        </div>
      )}
      {(context?.platform_admin || context?.partners.some((partner) => partner.role === "partner_admin")) && (
        <div className="panel">
          <button type="button" aria-expanded={showClientForm} onClick={() => setShowClientForm((value) => !value)}>
            {showClientForm ? "Fechar cadastro" : "+ Novo cliente"}
          </button>
          {showClientForm && <div>
          <h2>Cadastrar novo cliente</h2>
          <p>O cliente ficará vinculado ao parceiro selecionado. O portal do cliente inicia desabilitado.</p>
          <form onSubmit={(event) => void createClient(event)} style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
            <label>Parceiro{" "}
              <select required value={clientPartnerId} onChange={(event) => setClientPartnerId(event.target.value)}>
                <option value="">Selecione</option>
                {(context?.platform_admin ? directory : context?.partners.filter((partner) => partner.role === "partner_admin") ?? []).map((partner) => (
                  <option key={partner.id} value={partner.id}>{partner.name}</option>
                ))}
              </select>
            </label>
            <label>Empresa <input required minLength={2} maxLength={180} value={clientName} onChange={(event) => setClientName(event.target.value)} /></label>
            <label>Responsável <input required minLength={3} maxLength={120} value={clientResponsible} onChange={(event) => setClientResponsible(event.target.value)} /></label>
            <label>E-mail <input required type="email" value={clientEmail} onChange={(event) => setClientEmail(event.target.value)} /></label>
            <button type="submit" disabled={clientCreating}>{clientCreating ? "Cadastrando..." : "Cadastrar cliente"}</button>
          </form>
          {createdClient && <div role="status">
            <p><strong>{createdClient.company_name}</strong> cadastrado. Guarde a senha provisória antes de sair desta página.</p>
            <p>Login: {createdClient.email}</p>
            <p>Senha provisória: <code>{createdClient.temporary_password}</code></p>
          </div>}
        </div>
      )}
      {loading ? <p>Carregando carteira...</p> : (
        <>
          <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(155px, 1fr))", gap: 12 }}>
            <article className="panel"><strong>Empresas</strong><h2>{summary?.companies ?? companies.length}</h2></article>
            <article className="panel"><strong>Impressoras ativas</strong><h2>{summary?.active_printers ?? "—"}</h2></article>
            <article className="panel"><strong>Online</strong><h2>{summary?.online_printers ?? "—"}</h2></article>
            <article className="panel"><strong>Offline</strong><h2>{summary?.offline_printers ?? "—"}</h2></article>
            <article className="panel"><strong>Clientes com impressoras offline</strong><h2>{companiesNeedingAttention}</h2></article>
          </div>
          <div className="panel">
            <div className="partner-portfolio-filters" style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 16, alignItems: "center" }}>
              <label htmlFor="partner-company-search">Buscar cliente</label>
              <input id="partner-company-search" type="search" value={companySearch} onChange={(event) => setCompanySearch(event.target.value)} placeholder="Nome do cliente" />
              <label htmlFor="partner-company-status">Situação</label>
              <select id="partner-company-status" value={companyStatusFilter} onChange={(event) => setCompanyStatusFilter(event.target.value as "all" | "attention" | "online")}>
                <option value="all">Todos</option>
                <option value="attention">Com impressoras offline</option>
                <option value="online">Sem impressoras offline</option>
              </select>
              <span aria-live="polite">{visibleCompanies.length} cliente(s) exibido(s)</span>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead><tr><th scope="col">Empresa</th><th scope="col">Impressoras</th><th scope="col">Online</th><th scope="col">Offline</th><th scope="col">Portal do cliente</th><th scope="col">Ação</th></tr></thead>
              <tbody>
                {visibleCompanies.map((company) => {
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
            {companies.length > 0 && visibleCompanies.length === 0 && <p>Nenhum cliente corresponde aos filtros selecionados.</p>}
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
          {!fleetLoading && <div><h3>Alertas pendentes ({openAlertCount})</h3>
            {alerts.filter((item) => item.status !== "resolved").slice(0, 10).map((item) => (
              <p key={item.id}><strong>{item.severity.toUpperCase()}</strong> — {item.title}: {item.description}</p>
            ))}
          </div>}
        </div>
      )}
    </section>
  );
}
