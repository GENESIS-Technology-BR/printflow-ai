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
    <div className="printer-table-wrapper">
      <table className="printer-table">
        <thead>
          <tr>
            <th>Impressora</th>
            <th>IP</th>
            <th>Status</th>
            <th>Health</th>
            <th>Serial</th>
            <th>Páginas</th>
            <th>Toner</th>
            <th>Última comunicação</th>
          </tr>
        </thead>

        <tbody>
          {printers.map((printer) => (
            <tr
              key={
                printer.uuid ||
                printer.id ||
                printer.ip ||
                printer.name
              }
            >
              <td>
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
                    <small>
                      Origem: {printer.source || "Não informada"}
                    </small>
                  </div>
                </div>
              </td>

              <td>
                <code>
                  {printer.ip || "Não informado"}
                </code>
              </td>

              <td>
                <span
                  className={`status-pill status-${printer.status}`}
                >
                  <i />
                  {getStatusLabel(printer.status)}
                </span>
              </td>

              <td>
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
              </td>

              <td>
                <div>
                  <strong>{printer.serial || "Não disponível"}</strong>
                  {printer.serial_confidence !== null && (
                    <small>
                      {` ${printer.serial_confidence}%`}
                      {printer.serial_confirmed ? " • confirmado" : ""}
                    </small>
                  )}
                </div>
              </td>

              <td>
                {formatPages(printer.page_count)}
                {printer.page_count_confidence !== null && (
                  <small>{` ${printer.page_count_confidence}%`}</small>
                )}
              </td>

              <td>
                {printer.toner_percent === null
                  ? "Não disponível"
                  : `${printer.toner_percent}%`}
              </td>

              <td>
                {formatLastSeen(printer.last_seen)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
