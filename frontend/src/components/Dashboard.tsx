import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import MetricCard from "./MetricCard";

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
    status: null,
    name: null,
    version: null,
    last_seen: null,
    last_error: null,
  },
};

function formatNumber(
  value: number,
): string {
  return new Intl.NumberFormat(
    "pt-BR",
  ).format(value);
}

function formatUpdateDate(
  value: string | null,
): string {
  if (!value) {
    return "Aguardando dados";
  }

  const date = parseApiDate(value);

  if (Number.isNaN(date.getTime())) {
    return "Não informado";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "medium",
    },
  ).format(date);
}

function severityLabel(
  severity: OperationalAlert["severity"],
): string {
  if (severity === "critical") {
    return "Crítico";
  }

  if (severity === "warning") {
    return "Atenção";
  }

  return "Informativo";
}

function healthLabel(
  value: number,
): string {
  if (value >= 85) {
    return "Excelente";
  }

  if (value >= 70) {
    return "Boa";
  }

  if (value >= 50) {
    return "Atenção";
  }

  return "Crítica";
}

function healthColor(
  value: number,
): string {
  if (value >= 85) {
    return "#35dfad";
  }

  if (value >= 70) {
    return "#4b9dff";
  }

  if (value >= 50) {
    return "#ffb73f";
  }

  return "#ff5265";
}

export default function Dashboard({
  companyName,
  onManageCompany,
  onOpenPrinters,
}: DashboardProps) {
  const [summary, setSummary] =
    useState<DashboardSummary>(
      EMPTY_SUMMARY,
    );

  const [, setPrinters] =
    useState<DashboardPrinter[]>([]);

  const [alerts, setAlerts] =
    useState<OperationalAlert[]>([]);

  const [organizationUnits, setOrganizationUnits] =
    useState<OrganizationUnit[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const loadDashboard = useCallback(
    async (manual = false) => {
      if (manual) {
        setRefreshing(true);
      }

      try {
        const [
          summaryResponse,
          printersResponse,
          alertsResponse,
          unitsResponse,
        ] = await Promise.all([
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
    },
    [],
  );

  useEffect(() => {
    void loadDashboard();

    const intervalId =
      window.setInterval(
        () => {
          void loadDashboard();
        },
        30_000,
      );

    return () => {
      window.clearInterval(
        intervalId,
      );
    };
  }, [loadDashboard]);

  const openAlerts = useMemo(
    () =>
      alerts.filter(
        (alert) =>
          alert.status === "open",
      ),
    [alerts],
  );

  const priorityAlerts = useMemo(() => {
    const severityWeight = {
      critical: 3,
      warning: 2,
      info: 1,
    };

    return [...openAlerts]
      .sort(
        (a, b) =>
          severityWeight[b.severity] -
          severityWeight[a.severity],
      )
      .slice(0, 3);
  }, [openAlerts]);

  const unitCount =
    organizationUnits.length;

  const manufacturerCount =
    Object.keys(
      summary.manufacturers,
    ).length;

  const onlinePercent =
    summary.active_printers > 0
      ? Math.round(
          (
            summary.online /
            summary.active_printers
          ) * 100,
        )
      : 0;

  const offlinePercent =
    summary.active_printers > 0
      ? Math.round(
          (
            summary.offline /
            summary.active_printers
          ) * 100,
        )
      : 0;

  const hasMonitoringData =
    summary.active_printers > 0 ||
    summary.agent.last_seen !== null;

  const health = hasMonitoringData
    ? Math.max(
        0,
        Math.min(
          Math.round(
            summary.health_average,
          ),
          100,
        ),
      )
    : 0;

  const currentHealthColor =
    hasMonitoringData
      ? healthColor(health)
      : "#8ba2bd";

  const lastUpdate =
    summary.agent.last_seen ||
    summary.generated_at;

  return (
    <section className="dashboard-page executive-clean-page modern-dashboard clean-dashboard-v2">
      <header className="modern-dashboard-header">
        <div>
          <span className="modern-dashboard-kicker">
            Printflow · OPERAÇÕES
          </span>

          <h1>Visão geral</h1>

          <p>
            Acompanhe o desempenho e a saúde do
            parque de impressoras em tempo real.
          </p>
        </div>

        <div className="modern-dashboard-actions">
          <span
            className={
              summary.agent.online
                ? "modern-agent-badge online"
                : "modern-agent-badge offline"
            }
          >
            <i />

            {summary.agent.online
              ? `Agent online${
                  summary.agent.version
                    ? ` • v${summary.agent.version}`
                    : ""
                }`
              : "Agent sem comunicação"}
          </span>

          <button
            type="button"
            className="modern-refresh-button"
            disabled={refreshing}
            onClick={() =>
              void loadDashboard(true)
            }
          >
            <span>↻</span>

            {refreshing
              ? "Atualizando..."
              : "Atualizar"}
          </button>
        </div>
      </header>

      <div className="modern-update-row">
        <span>
          Última coleta:{" "}
          {formatUpdateDate(
            lastUpdate,
          )}
        </span>

      </div>

      <section className="modern-company-bar">
        <div className="modern-company-icon">
          ▦
        </div>

        <button
          type="button"
          className="modern-company-selector"
          onClick={onManageCompany}
          title="Gerenciar empresa monitorada"
        >
          <span>
            Empresa monitorada
          </span>

          <strong>
            {companyName}
          </strong>

          <i>⌄</i>
        </button>

        <button
          type="button"
          className="modern-company-manage"
          onClick={onManageCompany}
        >
          Gerenciar
        </button>
      </section>

      {error && (
        <div className="dashboard-error">
          <strong>
            Não foi possível atualizar os dados.
          </strong>

          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="modern-loading">
          Atualizando indicadores...
        </div>
      )}

      <div className="metrics-grid executive-clean-metrics modern-kpi-grid">
        <MetricCard
          title="Impressoras"
          value={
            summary.active_printers
          }
          icon="▣"
          color="#4b8dff"
          subtitle="Ativas monitoradas"
        />

        <MetricCard
          title="Online"
          value={summary.online}
          icon="◉"
          color="#35dfad"
          subtitle={`${onlinePercent}% do total`}
        />

        <MetricCard
          title="Offline"
          value={summary.offline}
          icon="⏻"
          color="#ff5265"
          subtitle={`${offlinePercent}% do total`}
        />

        <MetricCard
          title="Alertas"
          value={openAlerts.length}
          icon="△"
          color="#ffb23d"
          subtitle="Requerem atenção"
        />
      </div>

      <div className="clean-dashboard-main">
        <section className="modern-panel clean-health-card">
          <div className="clean-card-heading">
            <div>
              <span className="clean-card-kicker">
                SAÚDE DO PARQUE
              </span>

              <h2>Saúde do parque</h2>

              <p>
                Visão rápida da disponibilidade do ambiente.
              </p>
            </div>

            <strong
              className="clean-health-status"
              style={{ color: currentHealthColor }}
            >
              {hasMonitoringData
                ? healthLabel(health)
                : "Aguardando dados"}
            </strong>
          </div>

          <div className="clean-health-score-row">
            <div>
              <strong>
                {hasMonitoringData
                  ? `${health}%`
                  : "—"}
              </strong>
              <span>
                {hasMonitoringData
                  ? "saúde geral"
                  : "monitoramento não iniciado"}
              </span>
            </div>

            <div className="clean-health-progress">
              <i
                style={{
                  width: `${health}%`,
                  background: currentHealthColor,
                }}
              />
            </div>
          </div>

          <div className="clean-health-meta">
            <span>
              Disponibilidade
              <strong>{onlinePercent}%</strong>
            </span>

            <span>
              Agent
              <strong>
                {summary.agent.online
                  ? "Online"
                  : "Offline"}
              </strong>
            </span>
          </div>
        </section>

        <section className="modern-panel modern-alert-panel clean-alert-panel">
          <div className="modern-alert-heading">
            <div className="modern-panel-heading">
              <span className="modern-panel-icon alert">
                ♧
              </span>

              <div>
                <span className="modern-alert-kicker">
                  ATENÇÃO
                </span>

                <h2>
                  Alertas prioritários
                </h2>

                <p>
                  Somente o que precisa de ação.
                </p>
              </div>
            </div>

            <button
              type="button"
              className="modern-view-all"
              onClick={onOpenPrinters}
            >
              Ver impressoras →
            </button>
          </div>

          {priorityAlerts.length ? (
            <div className="modern-alert-list">
              {priorityAlerts.map(
                (alert) => (
                  <button
                    type="button"
                    className={
                      `modern-alert-item severity-${alert.severity}`
                    }
                    key={alert.id}
                    onClick={onOpenPrinters}
                  >
                    <i />

                    <div>
                      <strong>
                        {alert.title}
                      </strong>

                      <span>
                        {alert.description}
                      </span>
                    </div>

                    <small>
                      {severityLabel(
                        alert.severity,
                      )}
                    </small>

                    <b>›</b>
                  </button>
                ),
              )}
            </div>
          ) : (
            <div className="modern-no-alerts">
              <strong>
                {hasMonitoringData
                  ? "Tudo certo por aqui."
                  : "Monitoramento ainda não iniciado."}
              </strong>

              <span>
                {hasMonitoringData
                  ? "Nenhuma ação imediata necessária."
                  : "Instale e conecte o Agent para começar."}
              </span>
            </div>
          )}
        </section>
      </div>

      <section className="clean-summary-strip">
        <div className="clean-summary-item">
          <span>Páginas</span>
          <strong>
            {formatNumber(summary.total_pages)}
          </strong>
        </div>

        <div className="clean-summary-item">
          <span>Unidades</span>
          <strong>{unitCount}</strong>
        </div>

        <div className="clean-summary-item">
          <span>Fabricantes</span>
          <strong>{manufacturerCount}</strong>
        </div>

        <div className="clean-summary-item">
          <span>Contadores</span>
          <strong>
            {summary.page_count_known}
          </strong>
        </div>
      </section>

      <footer className="modern-dashboard-footer">
        Printflow — Gestão inteligente de
        impressão.
      </footer>
    </section>
  );
}
