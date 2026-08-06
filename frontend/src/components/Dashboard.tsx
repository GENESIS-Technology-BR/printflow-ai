import {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import AlertCenter from "./AlertCenter";
import FleetInsights from "./FleetInsights";
import HealthGauge from "./HealthGauge";
import MetricCard from "./MetricCard";
import PrinterTable from "./PrinterTable";

import {
  getDashboardPrinters,
  getDashboardSummary,
} from "../services/api";

import type {
  DashboardPrinter,
  DashboardSummary,
} from "../services/api";

import "./Dashboard.css";

const EMPTY_SUMMARY: DashboardSummary = {
  total_printers: 0,
  active_printers: 0,
  online: 0,
  offline: 0,
  unknown: 0,
  alerts: 0,
  total_pages: 0,
  health_average: 100,
  manufacturers: {},
  generated_at: "",
};

function formatNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function formatUpdateDate(value: string): string {
  if (!value) {
    return "Aguardando primeira atualização";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Atualização não informada";
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

export default function Dashboard() {
  const [summary, setSummary] =
    useState<DashboardSummary>(EMPTY_SUMMARY);

  const [printers, setPrinters] =
    useState<DashboardPrinter[]>([]);

  const [loading, setLoading] =
    useState(true);

  const [refreshing, setRefreshing] =
    useState(false);

  const [error, setError] =
    useState<string | null>(null);

  const loadDashboard = useCallback(
    async (manualRefresh = false) => {
      if (manualRefresh) {
        setRefreshing(true);
      }

      try {
        const [
          summaryResponse,
          printersResponse,
        ] = await Promise.all([
          getDashboardSummary(),
          getDashboardPrinters(),
        ]);

        setSummary(summaryResponse);
        setPrinters(printersResponse);
        setError(null);
      } catch (requestError) {
        const message =
          requestError instanceof Error
            ? requestError.message
            : "Falha ao carregar o Dashboard.";

        setError(message);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [],
  );

  useEffect(() => {
    void loadDashboard();

    const intervalId = window.setInterval(
      () => {
        void loadDashboard();
      },
      30_000,
    );

    return () => {
      window.clearInterval(intervalId);
    };
  }, [loadDashboard]);

  const criticalPrinters = useMemo(
    () =>
      printers.filter(
        (printer) =>
          printer.status === "offline" ||
          printer.health_score < 70,
      ).length,
    [printers],
  );

  return (
    <section className="dashboard-page">
      <header className="dashboard-header">
        <div>
          <span className="dashboard-eyebrow">
            PRINTFLOW EXECUTIVE CONTROL CENTER
          </span>

          <h1>Gestão inteligente do parque</h1>

          <p>
            Operação, disponibilidade, riscos e
            desempenho das impressoras em uma única visão.
          </p>
        </div>

        <div className="dashboard-header-actions">
          <span className="dashboard-live">
            <i />
            API conectada
          </span>

          <button
            type="button"
            className="dashboard-refresh"
            disabled={refreshing}
            onClick={() => {
              void loadDashboard(true);
            }}
          >
            {refreshing
              ? "Atualizando..."
              : "Atualizar dados"}
          </button>
        </div>
      </header>

      <div className="dashboard-update-row">
        <span>
          Última atualização:
          {" "}
          {formatUpdateDate(summary.generated_at)}
        </span>

        <span>
          Atualização automática a cada 30 segundos
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

      <div className="metrics-grid">
        <MetricCard
          title="Impressoras"
          value={summary.total_printers}
          icon="🖨️"
          color="#5ba8ff"
          subtitle={`${summary.active_printers} ativas`}
        />

        <MetricCard
          title="Online"
          value={summary.online}
          icon="●"
          color="#49d6a5"
          subtitle="Equipamentos disponíveis"
        />

        <MetricCard
          title="Offline"
          value={summary.offline}
          icon="●"
          color="#ff647c"
          subtitle="Requerem verificação"
        />

        <MetricCard
          title="Riscos"
          value={criticalPrinters}
          icon="⚠️"
          color="#ffbe55"
          subtitle="Equipamentos prioritários"
        />

        <MetricCard
          title="Páginas"
          value={formatNumber(summary.total_pages)}
          icon="📄"
          color="#ab8cff"
          subtitle="Contador acumulado"
        />
      </div>

      <HealthGauge
        value={summary.health_average}
      />

      <FleetInsights
        summary={summary}
        printers={printers}
      />

      <AlertCenter printers={printers} />

      <section className="dashboard-list-panel">
        <div className="dashboard-section-title">
          <div>
            <span>INVENTÁRIO</span>
            <h2>Impressoras monitoradas</h2>
          </div>

          <span className="dashboard-count">
            {printers.length} equipamento(s)
          </span>
        </div>

        {loading ? (
          <div className="dashboard-loading">
            <div className="dashboard-spinner" />
            <span>Carregando equipamentos...</span>
          </div>
        ) : (
          <PrinterTable printers={printers} />
        )}
      </section>

      <footer className="dashboard-footer">
        PRINTFLOW AI — Inteligência operacional
        para gestão de impressão.
      </footer>
    </section>
  );
}
