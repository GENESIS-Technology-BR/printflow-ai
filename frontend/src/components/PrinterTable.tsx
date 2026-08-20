import type {
  DashboardPrinter,
} from "../services/api";

type PrinterTableProps = {
  printers: DashboardPrinter[];
};

function formatPages(value: number | null): string {
  if (value === null) {
    return "Não disponível";
  }
  return new Intl.NumberFormat(
    "pt-BR",
  ).format(value);
}

function formatLastSeen(
  value: string | null,
): string {
  if (!value) {
    return "Sem comunicação";
  }

  const date = new Date(value);

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

function getStatusLabel(status: string): string {
  const normalized = status.toLowerCase();

  if (normalized === "online") {
    return "Online";
  }

  if (normalized === "offline") {
    return "Offline";
  }

  return "Desconhecido";
}

export default function PrinterTable({
  printers,
}: PrinterTableProps) {
  if (!printers.length) {
    return (
      <div className="dashboard-empty">
        <span>🖨️</span>

        <h3>Nenhuma impressora cadastrada</h3>

        <p>
          Instale o PRINTFLOW Agent na rede para
          iniciar a descoberta dos equipamentos.
        </p>
      </div>
    );
  }

  return (
    <div className="printer-cards">
      {printers.map((printer) => (
            <article
              className="printer-card"
              key={
                printer.uuid ||
                printer.id ||
                printer.ip ||
                printer.name
              }
            >
              <div className="printer-card-main">
                <div className="printer-identity">
                  <span className="printer-icon">
                    🖨️
                  </span>

                  <div>
                    <strong>{printer.name}</strong>

                    <span>
                      {printer.manufacturer ||
                        "Fabricante não identificado"}
                      {printer.model
                        ? ` • ${printer.model}`
                        : ""}
                    </span>
                    <small>Origem: {printer.source || "Não informada"}</small>
                  </div>
                </div>
                <div className="printer-connection">
                  <code>{printer.ip || "Não informado"}</code>
                <span
                  className={`status-pill status-${printer.status}`}
                >
                  <i />
                  {getStatusLabel(printer.status)}
                </span>
                </div>
                <div className="health-cell">
                  <strong>
                    {printer.health_score}%
                  </strong>

                  <div className="health-bar">
                    <span
                      style={{
                        width:
                          `${printer.health_score}%`,
                      }}
                    />
                  </div>
                </div>
              </div>

              <div className="printer-card-details">
                <div className="printer-detail">
                  <span>Serial</span>
                  <strong>{printer.serial || "Não disponível"}</strong>
                  {printer.serial_confidence !== null && (
                    <small>
                      {` ${printer.serial_confidence}%`}
                      {printer.serial_confirmed ? " • confirmado" : ""}
                    </small>
                  )}
                </div>
                <div className="printer-detail">
                  <span>Páginas</span>
                  <strong>{formatPages(printer.page_count)}</strong>
                {printer.page_count_confidence !== null && (
                  <small>{`${printer.page_count_confidence}% de confiança`}</small>
                )}
                </div>
                <div className="printer-detail">
                  <span>Toner</span>
                  <strong>{printer.toner_percent === null
                  ? "Não disponível"
                  : `${printer.toner_percent}%`}</strong>
                </div>
                <div className="printer-detail">
                  <span>Última comunicação</span>
                  <strong>{formatLastSeen(printer.last_seen)}</strong>
                </div>
              </div>
            </article>
          ))}
    </div>
  );
}
