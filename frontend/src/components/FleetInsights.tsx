import type {
  DashboardPrinter,
  DashboardSummary,
} from "../services/api";

type FleetInsightsProps = {
  summary: DashboardSummary;
  printers: DashboardPrinter[];
};

type ManufacturerItem = {
  name: string;
  total: number;
};

function formatNumber(value: number): string {
  return new Intl.NumberFormat("pt-BR").format(value);
}

function healthLabel(score: number): string {
  if (score >= 85) {
    return "Excelente";
  }

  if (score >= 70) {
    return "Boa";
  }

  if (score >= 50) {
    return "Atenção";
  }

  return "Crítica";
}

function buildManufacturers(
  summary: DashboardSummary,
): ManufacturerItem[] {
  return Object.entries(summary.manufacturers || {})
    .map(([name, total]) => ({
      name,
      total,
    }))
    .sort((first, second) => second.total - first.total)
    .slice(0, 6);
}

export default function FleetInsights({
  summary,
  printers,
}: FleetInsightsProps) {
  const manufacturers = buildManufacturers(summary);

  const maximumManufacturer = Math.max(
    ...manufacturers.map((item) => item.total),
    1,
  );

  const rankedPrinters = [...printers]
    .sort((first, second) => {
      if (first.health_score !== second.health_score) {
        return first.health_score - second.health_score;
      }

      return second.page_count - first.page_count;
    })
    .slice(0, 5);

  const onlinePercentage = summary.total_printers
    ? Math.round(
        summary.online * 100 / summary.total_printers,
      )
    : 100;

  return (
    <div className="executive-grid">
      <article className="executive-panel fleet-index-panel">
        <div className="executive-panel-header">
          <div>
            <span>PRINTFLOW INDEX</span>
            <h3>Condição operacional</h3>
          </div>

          <strong
            className={`fleet-index-value fleet-index-${healthLabel(
              summary.health_average,
            ).toLowerCase()}`}
          >
            {summary.health_average}
          </strong>
        </div>

        <div className="fleet-index-track">
          <span
            style={{
              width: `${summary.health_average}%`,
            }}
          />
        </div>

        <div className="fleet-index-metrics">
          <div>
            <strong>{healthLabel(summary.health_average)}</strong>
            <span>Saúde do parque</span>
          </div>

          <div>
            <strong>{onlinePercentage}%</strong>
            <span>Disponibilidade</span>
          </div>

          <div>
            <strong>
              {formatNumber(summary.total_pages)}
            </strong>
            <span>Páginas acumuladas</span>
          </div>
        </div>
      </article>

      <article className="executive-panel">
        <div className="executive-panel-header">
          <div>
            <span>FABRICANTES</span>
            <h3>Distribuição do parque</h3>
          </div>
        </div>

        {manufacturers.length ? (
          <div className="manufacturer-list">
            {manufacturers.map((manufacturer) => (
              <div
                className="manufacturer-item"
                key={manufacturer.name}
              >
                <div className="manufacturer-label">
                  <span>{manufacturer.name}</span>
                  <strong>{manufacturer.total}</strong>
                </div>

                <div className="manufacturer-track">
                  <span
                    style={{
                      width: `${
                        manufacturer.total *
                        100 /
                        maximumManufacturer
                      }%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="compact-empty">
            Fabricantes serão exibidos após o cadastro
            das impressoras.
          </div>
        )}
      </article>

      <article className="executive-panel executive-ranking">
        <div className="executive-panel-header">
          <div>
            <span>PRIORIDADES</span>
            <h3>Equipamentos que exigem atenção</h3>
          </div>
        </div>

        {rankedPrinters.length ? (
          <div className="ranking-list">
            {rankedPrinters.map((printer, index) => (
              <div
                className="ranking-item"
                key={
                  printer.uuid ||
                  printer.id ||
                  printer.ip ||
                  printer.name
                }
              >
                <span className="ranking-position">
                  {index + 1}
                </span>

                <div className="ranking-printer">
                  <strong>{printer.name}</strong>
                  <span>
                    {printer.ip || "IP não informado"}
                    {" • "}
                    {printer.manufacturer ||
                      "Fabricante desconhecido"}
                  </span>
                </div>

                <div className="ranking-health">
                  <strong>{printer.health_score}%</strong>
                  <span>
                    {healthLabel(printer.health_score)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="compact-empty">
            Nenhum equipamento disponível para o ranking.
          </div>
        )}
      </article>
    </div>
  );
}
