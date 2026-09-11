import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getDashboardPrinters,
  getDashboardSummary,
  getOperationalAlerts,
  getOrganizationUnits,
} from "../services/api";

import type {
  DashboardPrinter,
  DashboardSummary,
  OperationalAlert,
  OrganizationUnit,
} from "../services/api";

import { parseApiDate } from "../utils/dateTime";
import "./Dashboard.css";
import "./DashboardSap.css";

const DASHBOARD_REFRESH_MS = 5 * 60 * 1000;

type DashboardProps = {
  companyName: string;
  onManageCompany: () => void;
  onOpenPrinters: () => void;
};

const EMPTY_SUMMARY: DashboardSummary = {
  total_printers: 0,
  active_printers: 0,
  inactive_printers: 0,
  online: 0,
  offline: 0,
  unknown: 0,
  alerts: 0,
  total_pages: 0,
  page_count_known: 0,
  page_count_unknown: 0,
  health_average: 100,
  manufacturers: {},
  generated_at: "",
  agent: {
    online: false,
    stale: false,
    communication_state: "never_seen",
    age_seconds: null,
    status: null,
    name: null,
    version: null,
    last_seen: null,
    last_error: null,
  },
};

function formatNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function formatUpdateDate(value: string | null): string {
  if (!value) return "Aguardando dados";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "Não informado";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function displayPrinterName(printer: DashboardPrinter): string {
  return printer.custom_name || printer.hostname || printer.name || printer.ip || "Impressora";
}

function statusLabel(status: string): string {
  if (status === "online") return "Online";
  if (status === "offline") return "Offline";
  if (status === "inactive") return "Inativa";
  return "Desconhecido";
}

export default function Dashboard({
  companyName,
  onManageCompany,
  onOpenPrinters,
}: DashboardProps) {
  const [summary, setSummary] = useState<DashboardSummary>(EMPTY_SUMMARY);
  const [printers, setPrinters] = useState<DashboardPrinter[]>([]);
  const [alerts, setAlerts] = useState<OperationalAlert[]>([]);
  const [organizationUnits, setOrganizationUnits] = useState<OrganizationUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      const [summaryResponse, printersResponse, alertsResponse, unitsResponse] = await Promise.all([
        getDashboardSummary(),
        getDashboardPrinters(),
        getOperationalAlerts("all"),
        getOrganizationUnits(),
      ]);
      setSummary(summaryResponse);
      setPrinters(printersResponse);
      setAlerts(alertsResponse);
      setOrganizationUnits(unitsResponse);
      setError(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Falha ao carregar a Visão Geral.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
    const intervalId = window.setInterval(() => void loadDashboard(), DASHBOARD_REFRESH_MS);
    return () => window.clearInterval(intervalId);
  }, [loadDashboard]);

  const openAlerts = useMemo(
    () => alerts.filter((alert) => alert.status === "open"),
    [alerts],
  );

  const topPrinters = useMemo(
    () => [...printers]
      .filter((printer) => printer.active && printer.page_count !== null)
      .sort((a, b) => Number(b.page_count || 0) - Number(a.page_count || 0))
      .slice(0, 5),
    [printers],
  );

  const unitDistribution = useMemo(() => {
    const counts = new Map<string, number>();
    printers.filter((printer) => printer.active).forEach((printer) => {
      const unit = printer.unit_name || "Sem unidade";
      counts.set(unit, (counts.get(unit) || 0) + 1);
    });
    return [...counts.entries()]
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
  }, [printers]);

  const manufacturerDistribution = useMemo(() => {
    const entries = Object.entries(summary.manufacturers)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    const max = Math.max(1, ...entries.map(([, value]) => value));
    return entries.map(([name, value]) => ({ name, value, width: (value / max) * 100 }));
  }, [summary.manufacturers]);

  const onlinePercent = summary.active_printers > 0
    ? Math.round((summary.online / summary.active_printers) * 100)
    : 0;

  const knownPercent = summary.active_printers > 0
    ? Math.round((summary.page_count_known / summary.active_printers) * 100)
    : 0;

  const lastUpdate = summary.agent.last_seen || summary.generated_at;

  return (
    <section className="sap-dashboard-page">
      <div className="sap-page-head">
        <div>
          <div className="sap-breadcrumb">Home <span>/</span> Visão Geral</div>
          <h1>Visão Geral</h1>
          <p>Acompanhe em tempo real o desempenho do parque de impressão.</p>
        </div>
        <div className="sap-page-actions">
          <button type="button" className="sap-company-chip" onClick={onManageCompany}>
            <span>Empresa</span>
            <strong>{companyName}</strong>
          </button>
          <button
            type="button"
            className="sap-refresh"
            disabled={refreshing}
            onClick={() => void loadDashboard(true)}
          >
            {refreshing ? "Atualizando..." : "↻ Atualizar dados"}
          </button>
          <small>Última atualização: {formatUpdateDate(lastUpdate)}</small>
        </div>
      </div>

      {error && (
        <div className="sap-message-error">
          <strong>Não foi possível atualizar os dados.</strong>
          <span>{error}</span>
        </div>
      )}

      {loading && <div className="sap-loading">Atualizando indicadores...</div>}

      <div className="sap-kpi-grid">
        <article className="sap-kpi-card">
          <span className="sap-kpi-icon">▤</span>
          <div><small>Total de páginas</small><strong>{formatNumber(summary.total_pages)}</strong><em>contadores monitorados</em></div>
        </article>
        <article className="sap-kpi-card">
          <span className="sap-kpi-icon green">◉</span>
          <div><small>Impressoras ativas</small><strong>{summary.active_printers}</strong><em>{onlinePercent}% online</em></div>
        </article>
        <article className="sap-kpi-card">
          <span className="sap-kpi-icon">▦</span>
          <div><small>Unidades</small><strong>{organizationUnits.length}</strong><em>cadastradas</em></div>
        </article>
        <article className="sap-kpi-card">
          <span className="sap-kpi-icon">◎</span>
          <div><small>Contadores válidos</small><strong>{summary.page_count_known}</strong><em>{knownPercent}% do parque</em></div>
        </article>
        <article className="sap-kpi-card">
          <span className="sap-kpi-icon red">△</span>
          <div><small>Alertas</small><strong>{openAlerts.length}</strong><em>requerem atenção</em></div>
        </article>
      </div>

      <div className="sap-dashboard-grid sap-dashboard-grid-top">
        <article className="sap-panel sap-panel-wide">
          <header><div><span>PARQUE DE IMPRESSÃO</span><h2>Distribuição por fabricante</h2></div></header>
          <div className="sap-bars">
            {manufacturerDistribution.length ? manufacturerDistribution.map((item) => (
              <div className="sap-bar-row" key={item.name}>
                <span>{item.name || "Não identificado"}</span>
                <div><i style={{ width: `${item.width}%` }} /></div>
                <strong>{item.value}</strong>
              </div>
            )) : <p className="sap-empty">Sem dados de fabricantes.</p>}
          </div>
        </article>

        <article className="sap-panel sap-status-panel">
          <header><div><span>STATUS</span><h2>Status das impressoras</h2></div></header>
          <div className="sap-donut-wrap">
            <div className="sap-donut" style={{ "--online": `${onlinePercent * 3.6}deg` } as React.CSSProperties}>
              <div><strong>{summary.active_printers}</strong><span>total</span></div>
            </div>
            <div className="sap-status-list">
              <span><i className="online" />Online <strong>{summary.online}</strong></span>
              <span><i className="offline" />Offline <strong>{summary.offline}</strong></span>
              <span><i className="unknown" />Desconhecido <strong>{summary.unknown}</strong></span>
            </div>
          </div>
        </article>
      </div>

      <div className="sap-dashboard-grid sap-dashboard-grid-middle">
        <article className="sap-panel sap-panel-wide">
          <header>
            <div><span>UTILIZAÇÃO</span><h2>Impressoras com maior contador</h2></div>
            <button type="button" onClick={onOpenPrinters}>Ver todas</button>
          </header>
          <div className="sap-table-wrap">
            <table className="sap-table">
              <thead><tr><th>#</th><th>Impressora</th><th>Modelo</th><th>IP</th><th>Setor</th><th>Páginas</th><th>Status</th></tr></thead>
              <tbody>
                {topPrinters.map((printer, index) => (
                  <tr key={printer.uuid || printer.id || index}>
                    <td>{index + 1}</td>
                    <td><strong>{displayPrinterName(printer)}</strong></td>
                    <td>{printer.model || printer.manufacturer || "-"}</td>
                    <td>{printer.ip || "-"}</td>
                    <td>{printer.sector_name || "Não definido"}</td>
                    <td><strong>{formatNumber(Number(printer.page_count || 0))}</strong></td>
                    <td><span className={`sap-status-dot ${printer.status}`} />{statusLabel(printer.status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="sap-panel">
          <header><div><span>ORGANIZAÇÃO</span><h2>Equipamentos por unidade</h2></div></header>
          <div className="sap-unit-list">
            {unitDistribution.map((unit) => (
              <div key={unit.name}>
                <span>{unit.name}</span>
                <div><i style={{ width: `${Math.max(8, (unit.count / Math.max(1, summary.active_printers)) * 100)}%` }} /></div>
                <strong>{unit.count}</strong>
              </div>
            ))}
          </div>
        </article>
      </div>

      <div className="sap-dashboard-grid sap-dashboard-grid-bottom">
        <article className="sap-panel">
          <header><div><span>AGENT</span><h2>Comunicação</h2></div></header>
          <div className="sap-agent-card">
            <span className={summary.agent.online ? "online" : "offline"} />
            <div>
              <strong>{summary.agent.online ? "Agent online" : "Agent sem comunicação"}</strong>
              <p>{summary.agent.name || "PRINTFLOW Agent"}</p>
              <small>{summary.agent.version ? `Versão ${summary.agent.version}` : "Versão não informada"}</small>
            </div>
          </div>
        </article>

        <article className="sap-panel sap-panel-wide">
          <header>
            <div><span>ATENÇÃO</span><h2>Alertas prioritários</h2></div>
            <button type="button" onClick={onOpenPrinters}>Ver impressoras</button>
          </header>
          {openAlerts.length ? (
            <div className="sap-alert-list">
              {openAlerts.slice(0, 4).map((alert) => (
                <button type="button" key={alert.id} onClick={onOpenPrinters}>
                  <span className={`severity-${alert.severity}`} />
                  <div><strong>{alert.title}</strong><small>{alert.description}</small></div>
                  <b>›</b>
                </button>
              ))}
            </div>
          ) : (
            <div className="sap-no-alerts"><strong>Tudo certo por aqui.</strong><span>Nenhuma ação imediata necessária.</span></div>
          )}
        </article>
      </div>
    </section>
  );
}
