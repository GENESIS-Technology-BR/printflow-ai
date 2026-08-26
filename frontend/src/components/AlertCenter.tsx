import { useMemo, useState } from "react";

import type { OperationalAlert } from "../services/api";

import { parseApiDate } from "../utils/dateTime";

type AlertCenterProps = {
  alerts: OperationalAlert[];
  onAcknowledge: (alertId: number) => Promise<void>;
};
type StatusFilter = "open" | "acknowledged" | "resolved" | "all";
type SeverityFilter = OperationalAlert["severity"] | "all";

function severityLabel(severity: OperationalAlert["severity"]): string {
  if (severity === "critical") return "Crítico";
  if (severity === "warning") return "Atenção";
  return "Informativo";
}

function formatDate(value: string | null): string {
  if (!value) return "Horário indisponível";
  const date = parseApiDate(value);
  return Number.isNaN(date.getTime())
    ? "Horário indisponível"
    : new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(date);
}

export default function AlertCenter({ alerts, onAcknowledge }: AlertCenterProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("open");
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>("all");
  const [query, setQuery] = useState("");
  const [acknowledgingId, setAcknowledgingId] = useState<number | null>(null);

  const counts = useMemo(
    () => ({
      open: alerts.filter((alert) => alert.status === "open").length,
      acknowledged: alerts.filter((alert) => alert.status === "acknowledged").length,
      resolved: alerts.filter((alert) => alert.status === "resolved").length,
      critical: alerts.filter(
        (alert) => alert.status !== "resolved" && alert.severity === "critical",
      ).length,
    }),
    [alerts],
  );

  const visibleAlerts = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("pt-BR");
    return alerts
      .filter((alert) => statusFilter === "all" || alert.status === statusFilter)
      .filter(
        (alert) => severityFilter === "all" || alert.severity === severityFilter,
      )
      .filter((alert) => {
        if (!normalizedQuery) return true;
        return [alert.title, alert.description, alert.category]
          .join(" ")
          .toLocaleLowerCase("pt-BR")
          .includes(normalizedQuery);
      })
      .sort(
        (first, second) =>
          parseApiDate(second.last_seen_at).getTime() -
          parseApiDate(first.last_seen_at).getTime(),
      );
  }, [alerts, query, severityFilter, statusFilter]);

  return (
    <article className="dashboard-list-panel alert-center-panel">
      <div className="dashboard-section-title alert-center-heading">
        <div>
          <span>CENTRAL DE ALERTAS</span>
          <h2>Ocorrências e histórico operacional</h2>
        </div>
        <div className="alert-summary" aria-label="Resumo dos alertas">
          <span className="alert-summary-critical">{counts.critical} crítico(s)</span>
          <span>{counts.open} aberto(s)</span>
          <span>{counts.resolved} resolvido(s)</span>
        </div>
      </div>

      <div className="alert-toolbar">
        <div className="alert-status-tabs" aria-label="Filtrar por estado">
          {([
            ["open", `Abertos (${counts.open})`],
            ["acknowledged", `Reconhecidos (${counts.acknowledged})`],
            ["resolved", `Resolvidos (${counts.resolved})`],
            ["all", `Todos (${alerts.length})`],
          ] as const).map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={statusFilter === value ? "is-active" : ""}
              onClick={() => setStatusFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="alert-filters">
          <label>
            <span className="sr-only">Buscar ocorrências</span>
            <input
              type="search"
              value={query}
              placeholder="Buscar ocorrência..."
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <label>
            <span className="sr-only">Filtrar por severidade</span>
            <select
              value={severityFilter}
              onChange={(event) =>
                setSeverityFilter(event.target.value as SeverityFilter)
              }
            >
              <option value="all">Todas as severidades</option>
              <option value="critical">Crítico</option>
              <option value="warning">Atenção</option>
              <option value="info">Informativo</option>
            </select>
          </label>
        </div>
      </div>

      {!visibleAlerts.length ? (
        <div className="compact-empty alert-empty">
          {alerts.length
            ? "Nenhuma ocorrência corresponde aos filtros selecionados."
            : "Parque saudável. Nenhuma ocorrência registrada."}
        </div>
      ) : (
        <div className="alert-list">
          {visibleAlerts.map((alert) => (
            <div
              className={`alert-item alert-${alert.severity} alert-status-${alert.status}`}
              key={alert.id}
            >
              <span className="alert-indicator" />
              <div className="alert-content">
                <div className="alert-main">
                  <div className="alert-title-row">
                    <strong>{alert.title}</strong>
                    <span className={`alert-state alert-state-${alert.status}`}>
                      {alert.status === "open"
                        ? "Aberto"
                        : alert.status === "acknowledged"
                          ? "Reconhecido"
                          : "Resolvido"}
                    </span>
                  </div>
                  <span>{alert.description}</span>
                </div>
                <div className="alert-meta">
                  <strong>{severityLabel(alert.severity)}</strong>
                  <small>Aberto em {formatDate(alert.opened_at)}</small>
                  {alert.status === "resolved" && (
                    <small>Resolvido em {formatDate(alert.resolved_at)}</small>
                  )}
                  {alert.status === "acknowledged" && (
                    <small>Reconhecido em {formatDate(alert.acknowledged_at)}</small>
                  )}
                  {alert.status === "open" && (
                    <button
                      type="button"
                      className="alert-acknowledge"
                      disabled={acknowledgingId === alert.id}
                      onClick={async () => {
                        setAcknowledgingId(alert.id);
                        try {
                          await onAcknowledge(alert.id);
                        } finally {
                          setAcknowledgingId(null);
                        }
                      }}
                    >
                      {acknowledgingId === alert.id ? "Salvando..." : "Reconhecer"}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
