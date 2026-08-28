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

  const health = Math.max(
    0,
    Math.min(
      Math.round(
        summary.health_average,
      ),
      100,
    ),
  );

  const currentHealthColor =
    healthColor(health);

  const lastUpdate =
    summary.generated_at ||
    summary.agent.last_seen;

  return (
    <section className="dashboard-page executive-clean-page modern-dashboard">
      <header className="modern-dashboard-header">
        <div>
          <span className="modern-dashboard-kicker">
            PRINTFLOW AI · OPERAÇÕES
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
          Última atualização:{" "}
          {formatUpdateDate(
            lastUpdate,
          )}
        </span>

        <span>
          ↻ 30s
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
          subtitle="Total monitoradas"
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

      <div className="modern-dashboard-main">
        <section className="modern-panel modern-health-panel">
          <div className="modern-panel-heading">
            <span className="modern-panel-icon health">
              ♢
            </span>

            <div>
              <h2>
                Situação atual do ambiente
              </h2>

              <p>
                Resumo da saúde e qualidade do
                parque de impressoras.
              </p>
            </div>
          </div>

          <div className="modern-health-content">
            <div
              className="modern-health-gauge"
              style={{
                background: `conic-gradient(
                  ${currentHealthColor} ${health * 3.6}deg,
                  #17273b 0deg
                )`,
              }}
            >
              <div className="modern-health-gauge-center">
                <strong>{health}%</strong>
                <span>
                  Saúde geral
                  <br />
                  do parque
                </span>
              </div>
            </div>

            <div className="modern-health-information">
              <strong
                className="modern-health-label"
                style={{
                  color:
                    currentHealthColor,
                }}
              >
                {healthLabel(health)}
              </strong>

              <p>
                {health >= 85
                  ? "Ambiente estável e saudável. Continue assim!"
                  : "Existem pontos que precisam de acompanhamento."}
              </p>

              <div className="modern-health-stats">
                <div>
                  <span>
                    <i className="green" />
                    Disponibilidade
                  </span>

                  <strong>
                    {onlinePercent}%
                  </strong>
                </div>

                <div>
                  <span>
                    <i className="blue" />
                    Comunicação
                  </span>

                  <strong>
                    {summary.agent.online
                      ? "Online"
                      : "Offline"}
                  </strong>
                </div>

                <div>
                  <span>
                    <i className="green" />
                    Condição média
                  </span>

                  <strong>
                    {healthLabel(
                      health,
                    )}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="modern-panel modern-alert-panel">
          <div className="modern-alert-heading">
            <div className="modern-panel-heading">
              <span className="modern-panel-icon alert">
                ♧
              </span>

              <div>
                <span className="modern-alert-kicker">
                  ATENÇÃO AGORA
                </span>

                <h2>
                  Alertas prioritários
                </h2>

                <p>
                  Itens que requerem atenção
                  imediata.
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
                Ambiente sem alertas críticos.
              </strong>

              <span>
                Nenhuma ação imediata é
                necessária.
              </span>
            </div>
          )}
        </section>
      </div>

      <section className="modern-panel modern-summary-panel">
        <div className="modern-panel-heading">
          <span className="modern-panel-icon summary">
            ▤
          </span>

          <div>
            <span className="modern-summary-kicker">
              RESUMO OPERACIONAL
            </span>

            <h2>
              Resumo operacional
            </h2>

            <p>
              Principais indicadores de utilização
              e gestão do parque.
            </p>
          </div>
        </div>

        <div className="modern-summary-grid">
          <div className="modern-summary-item">
            <span className="summary-icon blue">
              ▤
            </span>

            <div>
              <strong>
                {formatNumber(
                  summary.total_pages,
                )}
              </strong>

              <span>
                Páginas acumuladas
              </span>

              <small>
                Total de páginas impressas
              </small>
            </div>
          </div>

          <div className="modern-summary-item">
            <span className="summary-icon cyan">
              ◇
            </span>

            <div>
              <strong>
                {unitCount}
              </strong>

              <span>
                Unidades cadastradas
              </span>

              <small>
                Equipamentos organizados
              </small>
            </div>
          </div>

          <div className="modern-summary-item">
            <span className="summary-icon purple">
              ▦
            </span>

            <div>
              <strong>
                {manufacturerCount}
              </strong>

              <span>
                Fabricantes
              </span>

              <small>
                Marcas diferentes no parque
              </small>
            </div>
          </div>

          <div className="modern-summary-item">
            <span className="summary-icon amber">
              ▣
            </span>

            <div>
              <strong>
                {summary.page_count_known}
              </strong>

              <span>
                Contadores conhecidos
              </span>

              <small>
                Equipamentos com contadores
              </small>
            </div>
          </div>
        </div>
      </section>

      <footer className="modern-dashboard-footer">
        PRINTFLOW AI — Gestão inteligente de
        impressão.
      </footer>
    </section>
  );
}
