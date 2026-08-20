import type {
  DashboardPrinter,
} from "../services/api";

type AlertCenterProps = {
  printers: DashboardPrinter[];
};

type AlertItem = {
  id: string;
  severity: "critical" | "warning" | "info";
  title: string;
  description: string;
};

function createAlerts(
  printers: DashboardPrinter[],
): AlertItem[] {
  const alerts: AlertItem[] = [];

  for (const printer of printers) {
    const printerId = String(
      printer.uuid ||
      printer.id ||
      printer.ip ||
      printer.name,
    );

    if (
      printer.status === "offline" ||
      !printer.active
    ) {
      alerts.push({
        id: `${printerId}-offline`,
        severity: "critical",
        title: `${printer.name} está offline`,
        description:
          printer.ip
            ? `Sem comunicação no endereço ${printer.ip}.`
            : "Equipamento sem comunicação.",
      });
    }

    if (printer.health_score < 50) {
      alerts.push({
        id: `${printerId}-health-critical`,
        severity: "critical",
        title: `Saúde crítica: ${printer.name}`,
        description:
          printer.health_reasons[0] ||
          "A impressora requer avaliação técnica.",
      });
    } else if (printer.health_score < 70) {
      alerts.push({
        id: `${printerId}-health-warning`,
        severity: "warning",
        title: `Atenção: ${printer.name}`,
        description:
          printer.health_reasons[0] ||
          "O PRINTFLOW Index está abaixo do recomendado.",
      });
    }

    if (
      printer.page_count !== null &&
      printer.page_count >= 500000
    ) {
      alerts.push({
        id: `${printerId}-page-count`,
        severity: "warning",
        title: `Contador elevado: ${printer.name}`,
        description:
          "Avaliar manutenção preventiva e vida útil do equipamento.",
      });
    }
  }

  if (!alerts.length && printers.length) {
    alerts.push({
      id: "fleet-healthy",
      severity: "info",
      title: "Parque sem riscos críticos",
      description:
        "Nenhuma ocorrência prioritária foi identificada.",
    });
  }

  return alerts.slice(0, 6);
}

function severityLabel(
  severity: AlertItem["severity"],
): string {
  if (severity === "critical") {
    return "Crítico";
  }

  if (severity === "warning") {
    return "Atenção";
  }

  return "Informativo";
}

export default function AlertCenter({
  printers,
}: AlertCenterProps) {
  const alerts = createAlerts(printers);

  return (
    <article className="dashboard-list-panel alert-center-panel">
      <div className="dashboard-section-title">
        <div>
          <span>CENTRAL DE ALERTAS</span>
          <h2>Ocorrências inteligentes</h2>
        </div>

        <span className="dashboard-count">
          {alerts.length} ocorrência(s)
        </span>
      </div>

      {!printers.length ? (
        <div className="compact-empty alert-empty">
          Os alertas serão gerados automaticamente
          quando as impressoras forem cadastradas.
        </div>
      ) : (
        <div className="alert-list">
          {alerts.map((alert) => (
            <div
              className={`alert-item alert-${alert.severity}`}
              key={alert.id}
            >
              <span className="alert-indicator" />

              <div className="alert-content">
                <div>
                  <strong>{alert.title}</strong>
                  <span>{alert.description}</span>
                </div>

                <small>
                  {severityLabel(alert.severity)}
                </small>
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
