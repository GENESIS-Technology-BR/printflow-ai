import type { OperationalAlert } from "../services/api";

type AlertCenterProps = { alerts: OperationalAlert[] };

function severityLabel(severity: OperationalAlert["severity"]): string {
  if (severity === "critical") return "Crítico";
  if (severity === "warning") return "Atenção";
  return "Informativo";
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Horário indisponível"
    : new Intl.DateTimeFormat("pt-BR", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(date);
}

export default function AlertCenter({ alerts }: AlertCenterProps) {
  const visibleAlerts = alerts.slice(0, 8);
  return (
    <article className="dashboard-list-panel alert-center-panel">
      <div className="dashboard-section-title">
        <div>
          <span>CENTRAL DE ALERTAS</span>
          <h2>Ocorrências operacionais</h2>
        </div>
        <span className="dashboard-count">{alerts.length} aberta(s)</span>
      </div>
      {!visibleAlerts.length ? (
        <div className="compact-empty alert-empty">
          Parque saudável. Nenhuma ocorrência aberta.
        </div>
      ) : (
        <div className="alert-list">
          {visibleAlerts.map((alert) => (
            <div className={`alert-item alert-${alert.severity}`} key={alert.id}>
              <span className="alert-indicator" />
              <div className="alert-content">
                <div>
                  <strong>{alert.title}</strong>
                  <span>{alert.description}</span>
                </div>
                <small>
                  {severityLabel(alert.severity)} • {formatDate(alert.opened_at)}
                </small>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
