import { useEffect, useMemo, useState } from "react";

import type { DashboardPrinter, OperationalAlert } from "../services/api";
import { getOperationalAlerts } from "../services/api";
import { parseApiDate } from "../utils/dateTime";

type ClientPrinterTableProps = {
  printers: DashboardPrinter[];
};

function formatPages(value: number | null): string {
  return value === null
    ? "Não disponível"
    : new Intl.NumberFormat("pt-BR").format(value);
}

function formatLastSeen(value: string | null): string {
  if (!value) return "Sem comunicação";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "Não informado";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function getStatusLabel(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "online") return "Online";
  if (normalized === "offline") return "Offline";
  if (normalized === "inactive") return "Inativo";
  return "Desconhecido";
}

function getPrinterKey(printer: DashboardPrinter): string {
  return String(printer.uuid || printer.id || printer.ip || printer.name);
}

function manufacturerBadge(printer: DashboardPrinter): string {
  const source = [printer.manufacturer, printer.model, printer.name]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  if (source.includes("hewlett") || /(^|\s)hp([\s-]|$)/.test(source)) return "HP";
  if (source.includes("ricoh")) return "RIC";
  if (source.includes("canon")) return "CAN";
  if (source.includes("brother")) return "BRO";
  if (source.includes("epson")) return "EPS";
  if (source.includes("kyocera")) return "KYO";
  if (source.includes("xerox")) return "XRX";
  if (source.includes("lexmark")) return "LEX";
  return String(printer.manufacturer || "PF").slice(0, 3).toUpperCase();
}

export default function ClientPrinterTable({
  printers,
}: ClientPrinterTableProps) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<OperationalAlert[]>([]);

  useEffect(() => {
    void getOperationalAlerts("open")
      .then(setAlerts)
      .catch(() => setAlerts([]));
  }, []);

  const sectors = useMemo(
    () => Array.from(
      new Set(
        printers
          .map((printer) => printer.sector_name)
          .filter((value): value is string => Boolean(value)),
      ),
    ).sort((a, b) => a.localeCompare(b, "pt-BR")),
    [printers],
  );

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return printers.filter((printer) => {
      const status = printer.status.toLowerCase();
      const matchesStatus = statusFilter === "all" || status === statusFilter;
      const matchesSector = sectorFilter === "all" || printer.sector_name === sectorFilter;
      const haystack = [
        printer.custom_name,
        printer.name,
        printer.ip,
        printer.serial,
        printer.model,
        printer.manufacturer,
        printer.sector_name,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesStatus && matchesSector && (!needle || haystack.includes(needle));
    });
  }, [printers, search, sectorFilter, statusFilter]);

  function alertLevel(printer: DashboardPrinter): "none" | "warning" | "critical" {
    const related = alerts.filter(
      (alert) => printer.id !== null && alert.printer_id === printer.id,
    );
    if (
      printer.status.toLowerCase() === "offline" ||
      printer.health_status === "critical" ||
      related.some((alert) => alert.severity === "critical")
    ) return "critical";
    if (
      printer.health_status === "attention" ||
      related.some((alert) => alert.severity === "warning")
    ) return "warning";
    return "none";
  }

  if (!printers.length) {
    return (
      <div className="dashboard-empty">
        <span>🖨️</span>
        <h3>Nenhum equipamento disponível</h3>
        <p>O parque monitorado ainda não possui dados disponíveis para consulta.</p>
      </div>
    );
  }

  return (
    <div className="printer-list-shell printer-clean-shell client-printer-shell">
      <div className="printer-filter-bar printer-clean-filter-bar">
        <input
          className="printer-search"
          type="search"
          placeholder="Buscar por nomenclatura, IP, série ou modelo..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          <option value="all">Todos os status</option>
          <option value="online">Online</option>
          <option value="offline">Offline</option>
          <option value="inactive">Inativos</option>
          <option value="unknown">Desconhecidos</option>
        </select>
        <select value={sectorFilter} onChange={(event) => setSectorFilter(event.target.value)}>
          <option value="all">Todos os setores</option>
          {sectors.map((sector) => <option key={sector} value={sector}>{sector}</option>)}
        </select>
        <span className="printer-filter-count">{filtered.length} de {printers.length}</span>
      </div>

      {!filtered.length && (
        <div className="printer-filter-empty">Nenhum equipamento encontrado com os filtros atuais.</div>
      )}

      <div className="printer-workspace-columns" aria-hidden="true">
        <span>Nomenclatura / identificação</span>
        <span>Páginas</span>
        <span>Toner</span>
        <span>Saúde</span>
        <span>Última comunicação</span>
        <span>Detalhes</span>
      </div>

      <div className="printer-cards printer-clean-cards">
        {filtered.map((printer) => {
          const key = getPrinterKey(printer);
          const expanded = expandedKey === key;
          const level = alertLevel(printer);
          const displayName = printer.custom_name || printer.name;
          const modelLabel = [printer.manufacturer, printer.model].filter(Boolean).join(" · ") || "Modelo não identificado";
          const sectorLabel = printer.sector_name || "Setor não informado";
          const tonerLabel = printer.toner_percent === null ? "—" : `${printer.toner_percent}%`;

          return (
            <article
              key={key}
              className={`printer-card printer-clean-card ${expanded ? "is-expanded" : ""} ${level !== "none" ? `printer-alert-${level}` : ""}`}
            >
              <div className="printer-clean-summary">
                <div className="printer-clean-identity">
                  <span className="printer-clean-icon">{manufacturerBadge(printer)}</span>
                  <div>
                    <div className="printer-clean-name-row">
                      <strong>{displayName}</strong>
                      {level !== "none" && (
                        <span className={`printer-attention-badge printer-attention-${level}`}>
                          <i aria-hidden="true" />
                          {level === "critical" ? "Crítico" : "Atenção"}
                        </span>
                      )}
                      <span className={`status-pill status-${printer.status}`}>
                        <i />{getStatusLabel(printer.status)}
                      </span>
                    </div>
                    <span className="printer-clean-model">{modelLabel}</span>
                    <div className="printer-clean-meta-row">
                      <code>{printer.ip || "IP não informado"}</code>
                      <span>{sectorLabel}</span>
                    </div>
                  </div>
                </div>

                <div className="printer-clean-stat">
                  <span>Páginas</span>
                  <strong>{formatPages(printer.page_count)}</strong>
                </div>

                <div className="printer-clean-stat printer-clean-toner">
                  <span>Toner</span>
                  <strong>{tonerLabel}</strong>
                  {printer.toner_percent !== null && (
                    <div className="printer-clean-mini-track">
                      <span style={{ width: `${printer.toner_percent}%` }} />
                    </div>
                  )}
                </div>

                <div className="printer-clean-stat printer-clean-health">
                  <span>Saúde</span>
                  <strong>{printer.health_score}%</strong>
                  <div className="printer-clean-mini-track">
                    <span style={{ width: `${printer.health_score}%` }} />
                  </div>
                </div>

                <div className="printer-clean-stat printer-clean-last-seen">
                  <span>Última comunicação</span>
                  <strong>{formatLastSeen(printer.last_seen)}</strong>
                </div>

                <button
                  type="button"
                  className="printer-clean-details-button"
                  aria-expanded={expanded}
                  onClick={() => setExpandedKey(expanded ? null : key)}
                >
                  {expanded ? "Fechar" : "Ver"}
                  <span aria-hidden="true">{expanded ? "↑" : "↓"}</span>
                </button>
              </div>

              {expanded && (
                <div className="printer-clean-details">
                  <section className="printer-clean-edit-section">
                    <div className="printer-clean-section-title">
                      <span>Informações do equipamento</span>
                      <small>Consulta operacional somente leitura</small>
                    </div>
                    <div className="printer-clean-technical-grid">
                      <div><span>Nomenclatura</span><strong>{displayName}</strong></div>
                      <div><span>IP</span><strong>{printer.ip || "Não informado"}</strong></div>
                      <div><span>Nº de série</span><strong>{printer.serial || "Não disponível"}</strong></div>
                      <div><span>Setor</span><strong>{sectorLabel}</strong></div>
                      <div><span>Modelo</span><strong>{modelLabel}</strong></div>
                      <div><span>Status</span><strong>{getStatusLabel(printer.status)}</strong></div>
                    </div>
                  </section>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
