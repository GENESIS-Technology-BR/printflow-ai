import { useEffect, useState } from "react";

import type {
  DashboardPrinter,
  OrganizationSector,
  OrganizationUnit,
} from "../services/api";

import {
  createOrganizationSector,
  createOrganizationUnit,
  getOrganizationSectors,
  getOrganizationUnits,
  updatePrinterCost,
  updatePrinterCustomName,
  updatePrinterOrganization,
} from "../services/api";

import { parseApiDate } from "../utils/dateTime";

type PrinterTableProps = {
  printers: DashboardPrinter[];
  defaultCostPerPage: number;
};

type OrganizationDraft = {
  unit_name: string;
  sector_name: string;
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

function formatRate(value: number): string {
  return `R$ ${Number(value || 0).toFixed(4).replace(".", ",")}`;
}

function getStatusLabel(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "online") return "Online";
  if (normalized === "offline") return "Offline";
  if (normalized === "inactive") return "Inativo";
  return "Desconhecido";
}

export default function PrinterTable({
  printers,
  defaultCostPerPage,
}: PrinterTableProps) {
  const [draftNames, setDraftNames] = useState<Record<string, string>>({});
  const [organizationDrafts, setOrganizationDrafts] = useState<Record<string, OrganizationDraft>>({});
  const [costDrafts, setCostDrafts] = useState<Record<string, string>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [unitFilter, setUnitFilter] = useState("all");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [catalogUnits, setCatalogUnits] = useState<OrganizationUnit[]>([]);
  const [catalogSectors, setCatalogSectors] = useState<OrganizationSector[]>([]);
  const [newUnitName, setNewUnitName] = useState("");
  const [newSectorName, setNewSectorName] = useState("");
  const [newSectorUnitId, setNewSectorUnitId] = useState("");
  const [catalogSaving, setCatalogSaving] = useState<"unit" | "sector" | null>(null);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [catalogMessage, setCatalogMessage] = useState<string | null>(null);

  async function loadOrganizationCatalog(): Promise<void> {
    try {
      const [unitsResponse, sectorsResponse] = await Promise.all([
        getOrganizationUnits(),
        getOrganizationSectors(),
      ]);
      setCatalogUnits(unitsResponse);
      setCatalogSectors(sectorsResponse);
      if (!newSectorUnitId && unitsResponse.length) {
        setNewSectorUnitId(String(unitsResponse[0].id));
      }
    } catch (error) {
      setCatalogError(
        error instanceof Error
          ? error.message
          : "Falha ao carregar unidades e setores.",
      );
    }
  }

  useEffect(() => {
    void loadOrganizationCatalog();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setSectorFilter("all");
  }, [unitFilter]);

  function currentCustomName(printer: DashboardPrinter): string {
    if (!printer.uuid) return printer.custom_name || "";
    return draftNames[printer.uuid] ?? printer.custom_name ?? "";
  }

  function currentOrganization(printer: DashboardPrinter): OrganizationDraft {
    if (printer.uuid && organizationDrafts[printer.uuid]) {
      return organizationDrafts[printer.uuid];
    }
    return {
      unit_name: printer.unit_name || "",
      sector_name: printer.sector_name || "",
    };
  }

  function currentCost(printer: DashboardPrinter): string {
    if (!printer.uuid) {
      return printer.cost_per_page === null
        ? ""
        : Number(printer.cost_per_page).toFixed(4);
    }
    if (costDrafts[printer.uuid] !== undefined) return costDrafts[printer.uuid];
    return printer.cost_per_page === null
      ? ""
      : Number(printer.cost_per_page).toFixed(4);
  }

  const units = Array.from(new Set([
    ...catalogUnits.map((unit) => unit.name),
    ...printers.map((printer) => currentOrganization(printer).unit_name).filter(Boolean),
  ])).sort((a, b) => a.localeCompare(b, "pt-BR"));

  const selectedCatalogUnit = catalogUnits.find((unit) => unit.name === unitFilter);
  const sectors = Array.from(new Set([
    ...catalogSectors
      .filter((sector) => unitFilter === "all" || !selectedCatalogUnit || sector.unit_id === selectedCatalogUnit.id)
      .map((sector) => sector.name),
    ...printers
      .filter((printer) => unitFilter === "all" || currentOrganization(printer).unit_name === unitFilter)
      .map((printer) => currentOrganization(printer).sector_name)
      .filter(Boolean),
  ])).sort((a, b) => a.localeCompare(b, "pt-BR"));

  const normalizedSearch = search.trim().toLowerCase();
  const filteredPrinters = printers.filter((printer) => {
    const organization = currentOrganization(printer);
    const status = printer.status.toLowerCase();
    if (statusFilter !== "all" && status !== statusFilter) return false;
    if (unitFilter !== "all" && organization.unit_name !== unitFilter) return false;
    if (sectorFilter !== "all" && organization.sector_name !== sectorFilter) return false;
    if (!normalizedSearch) return true;
    const searchable = [
      printer.name,
      currentCustomName(printer),
      printer.hostname,
      printer.ip,
      printer.serial,
      printer.manufacturer,
      printer.model,
      organization.unit_name,
      organization.sector_name,
    ];
    return searchable.some((value) =>
      String(value || "").toLowerCase().includes(normalizedSearch),
    );
  });

  async function createUnit(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const name = newUnitName.trim();
    if (name.length < 2) {
      setCatalogError("Informe o nome da unidade.");
      return;
    }
    try {
      setCatalogSaving("unit");
      setCatalogError(null);
      setCatalogMessage(null);
      const created = await createOrganizationUnit(name);
      setCatalogUnits((current) =>
        [...current, created].sort((a, b) => a.name.localeCompare(b.name, "pt-BR")),
      );
      if (!newSectorUnitId) setNewSectorUnitId(String(created.id));
      setNewUnitName("");
      setCatalogMessage(`Unidade "${created.name}" cadastrada.`);
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : "Falha ao cadastrar unidade.");
    } finally {
      setCatalogSaving(null);
    }
  }

  async function createSector(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const unitId = Number(newSectorUnitId);
    const name = newSectorName.trim();
    if (!unitId) {
      setCatalogError("Selecione uma unidade para o setor.");
      return;
    }
    if (name.length < 2) {
      setCatalogError("Informe o nome do setor.");
      return;
    }
    try {
      setCatalogSaving("sector");
      setCatalogError(null);
      setCatalogMessage(null);
      const created = await createOrganizationSector(unitId, name);
      setCatalogSectors((current) =>
        [...current, created].sort((a, b) => a.name.localeCompare(b.name, "pt-BR")),
      );
      setNewSectorName("");
      setCatalogMessage(`Setor "${created.name}" cadastrado.`);
    } catch (error) {
      setCatalogError(error instanceof Error ? error.message : "Falha ao cadastrar setor.");
    } finally {
      setCatalogSaving(null);
    }
  }

  async function saveCustomName(printer: DashboardPrinter): Promise<void> {
    if (!printer.uuid) return;
    try {
      setSavingKey(`name:${printer.uuid}`);
      setSaveError(null);
      const result = await updatePrinterCustomName(
        printer.uuid,
        currentCustomName(printer).trim() || null,
      );
      setDraftNames((current) => ({
        ...current,
        [printer.uuid as string]: result.custom_name || "",
      }));
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Falha ao salvar o nome personalizado.");
    } finally {
      setSavingKey(null);
    }
  }

  async function saveOrganization(printer: DashboardPrinter): Promise<void> {
    if (!printer.uuid) return;
    const organization = currentOrganization(printer);
    try {
      setSavingKey(`org:${printer.uuid}`);
      setSaveError(null);
      const result = await updatePrinterOrganization(
        printer.uuid,
        organization.unit_name.trim() || null,
        organization.sector_name.trim() || null,
      );
      setOrganizationDrafts((current) => ({
        ...current,
        [printer.uuid as string]: {
          unit_name: result.unit_name || "",
          sector_name: result.sector_name || "",
        },
      }));
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Falha ao salvar unidade e setor.");
    } finally {
      setSavingKey(null);
    }
  }

  async function saveCost(printer: DashboardPrinter): Promise<void> {
    if (!printer.uuid) return;
    const raw = currentCost(printer).trim().replace(",", ".");
    const value = raw === "" ? null : Number(raw);
    if (value !== null && (!Number.isFinite(value) || value < 0 || value > 100)) {
      setSaveError("Informe um custo por página entre 0 e 100, ou deixe vazio para usar o padrão da empresa.");
      return;
    }
    try {
      setSavingKey(`cost:${printer.uuid}`);
      setSaveError(null);
      const result = await updatePrinterCost(printer.uuid, value);
      setCostDrafts((current) => ({
        ...current,
        [printer.uuid as string]: result.cost_per_page === null
          ? ""
          : Number(result.cost_per_page).toFixed(4),
      }));
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : "Falha ao salvar custo por página.");
    } finally {
      setSavingKey(null);
    }
  }

  function changeOrganization(
    printer: DashboardPrinter,
    field: keyof OrganizationDraft,
    value: string,
  ): void {
    if (!printer.uuid) return;
    const current = currentOrganization(printer);
    setOrganizationDrafts((drafts) => ({
      ...drafts,
      [printer.uuid as string]: {
        ...current,
        [field]: value,
        ...(field === "unit_name" ? { sector_name: "" } : {}),
      },
    }));
  }

  if (!printers.length) {
    return (
      <div className="dashboard-empty">
        <span>🖨️</span>
        <h3>Nenhuma impressora cadastrada</h3>
        <p>Instale o PRINTFLOW Agent na rede para iniciar a descoberta dos equipamentos.</p>
      </div>
    );
  }

  return (
    <div className="printer-list-shell">
      <section className="printer-organization-catalog">
        <div className="printer-organization-catalog-header">
          <div>
            <span>ORGANIZAÇÃO DO PARQUE</span>
            <h3>Unidades e setores</h3>
            <p>Cadastre a estrutura da empresa e depois associe cada impressora.</p>
          </div>
          <div className="printer-organization-totals">
            <strong>{catalogUnits.length}<small> unidades</small></strong>
            <strong>{catalogSectors.length}<small> setores</small></strong>
          </div>
        </div>

        <div className="printer-organization-create-grid">
          <form className="printer-organization-create" onSubmit={(event) => void createUnit(event)}>
            <label>
              Nova unidade
              <div>
                <input
                  type="text"
                  maxLength={120}
                  value={newUnitName}
                  placeholder="Ex.: Caxias do Sul"
                  onChange={(event) => setNewUnitName(event.target.value)}
                />
                <button type="submit" disabled={catalogSaving === "unit"}>
                  {catalogSaving === "unit" ? "Salvando..." : "+ Adicionar unidade"}
                </button>
              </div>
            </label>
          </form>

          <form className="printer-organization-create" onSubmit={(event) => void createSector(event)}>
            <label>
              Novo setor
              <div className="printer-sector-create-row">
                <select
                  value={newSectorUnitId}
                  disabled={!catalogUnits.length}
                  onChange={(event) => setNewSectorUnitId(event.target.value)}
                >
                  {!catalogUnits.length && <option value="">Cadastre uma unidade primeiro</option>}
                  {catalogUnits.map((unit) => (
                    <option key={unit.id} value={unit.id}>{unit.name}</option>
                  ))}
                </select>
                <input
                  type="text"
                  maxLength={120}
                  value={newSectorName}
                  placeholder="Ex.: Comercial"
                  disabled={!catalogUnits.length}
                  onChange={(event) => setNewSectorName(event.target.value)}
                />
                <button type="submit" disabled={!catalogUnits.length || catalogSaving === "sector"}>
                  {catalogSaving === "sector" ? "Salvando..." : "+ Adicionar setor"}
                </button>
              </div>
            </label>
          </form>
        </div>

        {catalogMessage && <div className="printer-catalog-message success">{catalogMessage}</div>}
        {catalogError && <div className="printer-catalog-message error">{catalogError}</div>}
      </section>

      <div className="printer-filter-bar">
        <input
          className="printer-search"
          type="search"
          placeholder="Buscar por nome, IP, host ou serial..."
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
        <select value={unitFilter} onChange={(event) => setUnitFilter(event.target.value)}>
          <option value="all">Todas as unidades</option>
          {units.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
        </select>
        <select value={sectorFilter} onChange={(event) => setSectorFilter(event.target.value)}>
          <option value="all">Todos os setores</option>
          {sectors.map((sector) => <option key={sector} value={sector}>{sector}</option>)}
        </select>
        <span className="printer-filter-count">{filteredPrinters.length} de {printers.length}</span>
      </div>

      {saveError && <div className="printer-alias-error">{saveError}</div>}
      {!filteredPrinters.length && (
        <div className="printer-filter-empty">Nenhuma impressora encontrada com os filtros atuais.</div>
      )}

      <div className="printer-cards">
        {filteredPrinters.map((printer) => {
          const organization = currentOrganization(printer);
          const printerCatalogUnit = catalogUnits.find((unit) => unit.name === organization.unit_name);
          const availableSectors = Array.from(new Set([
            ...catalogSectors
              .filter((sector) => !printerCatalogUnit || sector.unit_id === printerCatalogUnit.id)
              .map((sector) => sector.name),
            ...(organization.sector_name ? [organization.sector_name] : []),
          ])).sort((a, b) => a.localeCompare(b, "pt-BR"));
          const costInput = currentCost(printer);
          const hasSpecificCost = costInput.trim() !== "";

          return (
            <article
              className="printer-card"
              key={printer.uuid || printer.id || printer.ip || printer.name}
            >
              <div className="printer-card-main">
                <div className="printer-identity">
                  <span className="printer-icon">🖨️</span>
                  <div className="printer-identity-content">
                    <div className="printer-title-row">
                      <strong>{printer.name}</strong>
                      <form
                        className="printer-alias-editor"
                        onSubmit={(event) => {
                          event.preventDefault();
                          void saveCustomName(printer);
                        }}
                      >
                        <input
                          type="text"
                          maxLength={150}
                          value={currentCustomName(printer)}
                          placeholder="Nome personalizado"
                          onChange={(event) => {
                            if (!printer.uuid) return;
                            setDraftNames((current) => ({
                              ...current,
                              [printer.uuid as string]: event.target.value,
                            }));
                          }}
                        />
                        <button type="submit" disabled={!printer.uuid || savingKey === `name:${printer.uuid}`}>
                          {savingKey === `name:${printer.uuid}` ? "Salvando..." : "Salvar"}
                        </button>
                      </form>
                    </div>

                    <span>
                      {printer.manufacturer || "Fabricante não identificado"}
                      {printer.model ? ` • ${printer.model}` : ""}
                    </span>
                    <small className="printer-hostname">Host: {printer.hostname || "Não identificado"}</small>
                    <small>Origem: {printer.source || "Não informada"}</small>

                    <div className="printer-organization-editor">
                      <label>
                        Unidade
                        <select
                          value={organization.unit_name}
                          onChange={(event) => changeOrganization(printer, "unit_name", event.target.value)}
                        >
                          <option value="">Sem unidade</option>
                          {units.map((unit) => <option key={unit} value={unit}>{unit}</option>)}
                        </select>
                      </label>
                      <label>
                        Setor
                        <select
                          value={organization.sector_name}
                          disabled={!organization.unit_name}
                          onChange={(event) => changeOrganization(printer, "sector_name", event.target.value)}
                        >
                          <option value="">Sem setor</option>
                          {availableSectors.map((sector) => <option key={sector} value={sector}>{sector}</option>)}
                        </select>
                      </label>
                      <button
                        type="button"
                        onClick={() => void saveOrganization(printer)}
                        disabled={!printer.uuid || savingKey === `org:${printer.uuid}`}
                      >
                        {savingKey === `org:${printer.uuid}` ? "Salvando..." : "Salvar localização"}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="printer-connection">
                  <code>{printer.ip || "Não informado"}</code>
                  <span className={`status-pill status-${printer.status}`}>
                    <i />{getStatusLabel(printer.status)}
                  </span>
                </div>

                <div className="health-cell">
                  <strong>{printer.health_score}%</strong>
                  <div className="health-bar">
                    <span style={{ width: `${printer.health_score}%` }} />
                  </div>
                </div>
              </div>

              <div className="printer-card-details">
                <div className="printer-detail">
                  <span>Serial</span>
                  <strong>{printer.serial || "Não disponível"}</strong>
                  {printer.serial_confidence !== null && (
                    <small>{`${printer.serial_confidence}%${printer.serial_confirmed ? " • confirmado" : ""}`}</small>
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
                  <span>Custo por página</span>
                  <form
                    className="printer-alias-editor"
                    onSubmit={(event) => {
                      event.preventDefault();
                      void saveCost(printer);
                    }}
                  >
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="0.0001"
                      value={costInput}
                      placeholder={Number(defaultCostPerPage || 0).toFixed(4)}
                      onChange={(event) => {
                        if (!printer.uuid) return;
                        setCostDrafts((current) => ({
                          ...current,
                          [printer.uuid as string]: event.target.value,
                        }));
                      }}
                    />
                    <button type="submit" disabled={!printer.uuid || savingKey === `cost:${printer.uuid}`}>
                      {savingKey === `cost:${printer.uuid}` ? "Salvando..." : "Salvar"}
                    </button>
                  </form>
                  <small>
                    {hasSpecificCost
                      ? "Tarifa específica desta impressora"
                      : `Usando padrão: ${formatRate(defaultCostPerPage)}`}
                  </small>
                </div>

                <div className="printer-detail">
                  <span>Toner</span>
                  <strong>{printer.toner_percent === null ? "Não disponível" : `${printer.toner_percent}%`}</strong>
                </div>

                <div className="printer-detail">
                  <span>Última comunicação</span>
                  <strong>{formatLastSeen(printer.last_seen)}</strong>
                </div>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
