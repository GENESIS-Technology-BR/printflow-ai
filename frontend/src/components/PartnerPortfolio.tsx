import { useCallback, useEffect, useState } from "react";

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

type CompanyOverview = {
  company_id: number;
  total_active_printers: number;
  online_printers: number;
  offline_printers: number;
  agent_status: string | null;
};

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
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState("");

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

  async function setPortal(company: PartnerCompany) {
    const allowed = context?.platform_admin || context?.partners.some(
      (p) => p.id === company.partner_id && p.role === "partner_admin"
    );
    if (!allowed) return;
    setBusyId(company.id);
    setError("");
    try {
      await api(`/partners/companies/${company.id}/customer-portal`, {
        method: "PATCH",
        body: JSON.stringify({ enabled: !company.customer_portal_enabled }),
      });
      setCompanies((previous) => previous.map((item) =>
        item.id === company.id
          ? { ...item, customer_portal_enabled: !company.customer_portal_enabled }
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
      {loading ? <p>Carregando carteira...</p> : (
        <>
          <p>{companies.length} empresa(s) na carteira</p>
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
                      <td>{company.name}</td>
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
    </section>
  );
}
