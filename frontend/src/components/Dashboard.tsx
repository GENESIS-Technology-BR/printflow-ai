import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import HealthGauge from "./HealthGauge";
import MetricCard from "./MetricCard";

import {
  getDashboardPrinters,
  getDashboardSummary,
  getOperationalAlerts,
} from "../services/api";

import type {
  DashboardPrinter,
  DashboardSummary,
  OperationalAlert,
} from "../services/api";

import { parseApiDate } from "../utils/dateTime";

import "./Dashboard.css";

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
  value: string,
): string {
  if (!value) {
    return "Aguardando atualização";
  }

  const date = parseApiDate(value);

  if (Number.isNaN(date.getTime())) {
    return "Não informado";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "short",
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

export default function Dashboard() {
  const [summary, setSummary] =
    useState<DashboardSummary>(
      EMPTY_SUMMARY,
    );

  const [printers, setPrinters] =
    useState<DashboardPrinter[]>([]);

  const [alerts, setAlerts] =
    useState<OperationalAlert[]>([]);

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
        ] = await Promise.all([
          getDashboardSummary(),
          getDashboardPrinters(),
          getOperationalAlerts("all"),
        ]);

        setSummary(summaryResponse);
        setPrinters(printersResponse);
        setAlerts(alertsResponse);
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

  const priorityAlerts = useMemo(() => {
    const severityWeight = {
      critical: 3,
      warning: 2,
      info: 1,
    };

    return alerts
      .filter(
        (alert) =>
          alert.status === "open",
      )
      .sort(
        (a, b) =>
          severityWeight[b.severity] -
          severityWeight[a.severity],
      )
      .slice(0, 3);
  }, [alerts]);

  const unitCount = useMemo(
    () =>
      new Set(
        printers
          .filter(
            (printer) =>
              printer.active &&
              printer.unit_name,
          )
          .map(
            (printer) =>
              printer.unit_name,
          ),
      ).size,
    [printers],
  );

  const manufacturerCount =
    Object.keys(
      summary.manufacturers,
    ).length;

  return (
    <section className="dashboard-page executive-clean-page">
      <header className="dashboard-header executive-clean-header">
        <div>
          <span className="dashboard-eyebrow">
            PRINTFLOW · VISÃO GERAL
          </span>

          <h1>
            Situação atual do ambiente
          </h1>

          <p>
            Os indicadores essenciais para
            entender o parque em poucos segundos.
          </p>
        </div>

        <div className="dashboard-header-actions">
          <span className="dashboard-live">
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
            className="dashboard-refresh"
            disabled={refreshing}
            onClick={() =>
              void loadDashboard(true)
            }
          >
            {refreshing
              ? "Atualizando..."
              : "Atualizar"}
          </button>
        </div>
      </header>

      <div className="dashboard-update-row executive-clean-update">
        <span>
          Última atualização:{" "}
          {formatUpdateDate(
            summary.generated_at,
          )}
        </span>

        <span>
          Atualização automática • 30s
        </span>
      </div>

      {error && (
        <div className="dashboard-error">
          <strong>
            Não foi possível atualizar os dados.
          </strong>

          <span>{error}</span>
        </div>
      )}

      {loading && (
        <div className="executive-clean-loading">
          Atualizando indicadores...
        </div>
      )}

      <div className="metrics-grid executive-clean-metrics">
        <MetricCard
          title="Impressoras"
          value={
            summary.active_printers
          }
          icon="🖨️"
          color="#5ba8ff"
          subtitle="Parque monitorado"
        />

        <MetricCard
          title="Online"
          value={summary.online}
          icon="●"
          color="#49d6a5"
          subtitle="Disponíveis agora"
        />

        <MetricCard
          title="Offline"
          value={summary.offline}
          icon="●"
          color="#ff647c"
          subtitle="Requerem verificação"
        />

        <MetricCard
          title="Alertas"
          value={summary.alerts}
          icon="⚠️"
          color="#ffbe55"
          subtitle="Precisam de atenção"
        />
      </div>

      <div className="executive-clean-main">
        <HealthGauge
          value={
            summary.health_average
          }
        />

        <section className="executive-attention-panel">
          <div className="executive-clean-panel-title">
            <span>ATENÇÃO AGORA</span>

            <h2>
              O que precisa ser verificado
            </h2>
          </div>

          {priorityAlerts.length ? (
            <div className="executive-alert-list">
              {priorityAlerts.map(
                (alert) => (
                  <div
                    className={
                      `executive-alert-item executive-alert-${alert.severity}`
                    }
                    key={alert.id}
                  >
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
                  </div>
                ),
              )}
            </div>
          ) : summary.offline > 0 ? (
            <div className="executive-clean-state attention">
              <strong>
                {summary.offline} equipamento(s)
                offline.
              </strong>

              <span>
                Acesse Impressoras para
                investigar os equipamentos.
              </span>
            </div>
          ) : summary.alerts > 0 ? (
            <div className="executive-clean-state attention">
              <strong>
                Existem itens que precisam de
                atenção.
              </strong>

              <span>
                Consulte o monitoramento das
                impressoras.
              </span>
            </div>
          ) : (
            <div className="executive-clean-state success">
              <strong>
                Nenhuma ação imediata.
              </strong>

              <span>
                O ambiente está operando
                normalmente.
              </span>
            </div>
          )}
        </section>
      </div>

      <section className="executive-operational-summary">
        <div className="executive-clean-panel-title">
          <span>RESUMO OPERACIONAL</span>
          <h2>
            Indicadores complementares
          </h2>
        </div>

        <div className="executive-summary-values">
          <div>
            <strong>
              {formatNumber(
                summary.total_pages,
              )}
            </strong>
            <span>
              Páginas acumuladas
            </span>
          </div>

          <div>
            <strong>
              {unitCount}
            </strong>
            <span>
              Unidades cadastradas
            </span>
          </div>

          <div>
            <strong>
              {manufacturerCount}
            </strong>
            <span>
              Fabricantes
            </span>
          </div>

          <div>
            <strong>
              {summary.page_count_known}
            </strong>
            <span>
              Contadores conhecidos
            </span>
          </div>
        </div>
      </section>

      <div className="executive-clean-hint">
        Detalhes técnicos, busca, filtros,
        unidade, setor e edição ficam disponíveis
        no menu <strong>Impressoras</strong>.
      </div>

      <footer className="dashboard-footer">
        PRINTFLOW AI — Gestão inteligente
        de impressão.
      </footer>
    </section>
  );
}
