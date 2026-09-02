import { useEffect, useMemo, useState } from "react"

import {
  downloadUsageReport,
  getDashboardPrinters,
  getOrganizationSectors,
  getOrganizationUnits,
  getUsageReport,
} from "../services/api"
import type {
  DashboardPrinter,
  OrganizationSector,
  OrganizationUnit,
  UsageReportFilters,
  UsageReportRow,
} from "../services/api"

import "./Reports.css"

type ReportsProps = { companyName: string }

function inputDate(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}

function number(value: number | null): string {
  if (value === null) return "-"
  return new Intl.NumberFormat("pt-BR").format(value)
}

function currency(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value)
}

function rate(value: number): string {
  return `R$ ${Number(value || 0).toFixed(4).replace(".", ",")}`
}

function modelLabel(manufacturer: string | null, model: string | null): string {
  const brand = (manufacturer || "").trim()
  const modelText = (model || "").trim()
  if (!modelText) return brand || "-"
  if (brand && modelText.toLowerCase().startsWith(brand.toLowerCase())) return modelText
  return [brand, modelText].filter(Boolean).join(" ") || "-"
}

export default function Reports({ companyName }: ReportsProps) {
  const today = useMemo(() => new Date(), [])
  const initialStart = useMemo(() => {
    const start = new Date(today)
    start.setDate(start.getDate() - 30)
    return start
  }, [today])

  const [startDate, setStartDate] = useState(inputDate(initialStart))
  const [endDate, setEndDate] = useState(inputDate(today))
  const [unitName, setUnitName] = useState("")
  const [sectorName, setSectorName] = useState("")
  const [printerUuid, setPrinterUuid] = useState("")
  const [units, setUnits] = useState<OrganizationUnit[]>([])
  const [sectors, setSectors] = useState<OrganizationSector[]>([])
  const [printers, setPrinters] = useState<DashboardPrinter[]>([])
  const [rows, setRows] = useState<UsageReportRow[]>([])
  const [loading, setLoading] = useState(true)
  const [downloading, setDownloading] = useState<"xlsx" | "pdf" | null>(null)
  const [error, setError] = useState<string | null>(null)

  const filters = useMemo<UsageReportFilters>(() => ({
    startDate,
    endDate,
    unitName: unitName || undefined,
    sectorName: sectorName || undefined,
    printerUuid: printerUuid || undefined,
  }), [startDate, endDate, unitName, sectorName, printerUuid])

  useEffect(() => {
    let cancelled = false
    async function loadCatalogs() {
      try {
        const [unitsData, sectorsData, printersData] = await Promise.all([
          getOrganizationUnits(),
          getOrganizationSectors(),
          getDashboardPrinters(),
        ])
        if (cancelled) return
        setUnits(unitsData)
        setSectors(sectorsData)
        setPrinters(printersData)
      } catch {
        if (!cancelled) setError("Não foi possível carregar os filtros do relatório.")
      }
    }
    void loadCatalogs()
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    let cancelled = false
    async function loadReport() {
      setLoading(true)
      setError(null)
      try {
        const data = await getUsageReport(filters)
        if (!cancelled) setRows(data)
      } catch (requestError) {
        if (!cancelled) {
          setRows([])
          setError(requestError instanceof Error ? requestError.message : "Não foi possível carregar o relatório.")
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void loadReport()
    return () => { cancelled = true }
  }, [filters])

  const selectedUnit = units.find((unit) => unit.name === unitName)
  const availableSectors = selectedUnit
    ? sectors.filter((sector) => sector.unit_id === selectedUnit.id)
    : sectors

  const availablePrinters = printers.filter((printer) => {
    if (unitName && printer.unit_name !== unitName) return false
    if (sectorName && printer.sector_name !== sectorName) return false
    return true
  })

  const totalPages = rows.reduce((total, row) => total + row.pages_printed, 0)
  const totalAnomalies = rows.reduce((total, row) => total + row.anomaly_count, 0)
  const totalCost = rows.reduce((total, row) => total + row.estimated_cost, 0)

  async function handleDownload(format: "xlsx" | "pdf") {
    setDownloading(format)
    setError(null)
    try {
      const blob = await downloadUsageReport(format, filters)
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = objectUrl
      link.download = `printflow-${startDate}-${endDate}.${format}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "Não foi possível baixar o relatório.")
    } finally {
      setDownloading(null)
    }
  }

  return (
    <div className="reports-page">
      <header className="reports-header">
        <div>
          <small>GESTÃO DE CONSUMO E CUSTOS</small>
          <h1>Relatórios</h1>
          <p>{companyName}</p>
        </div>
        <span className="online">● Histórico ativo</span>
      </header>

      <section className="reports-intro">
        <div>
          <small>Printflow · CONSUMO FINANCEIRO POR IMPRESSORA</small>
          <h2>Fechamento de impressão por período</h2>
          <p>Consulte páginas, tarifa e custo estimado por equipamento e exporte em Excel ou PDF.</p>
        </div>
        <div className="reports-downloads">
          <button type="button" onClick={() => void handleDownload("xlsx")} disabled={loading || downloading !== null}>
            {downloading === "xlsx" ? "Gerando..." : "Baixar Excel"}
          </button>
          <button type="button" className="pdf" onClick={() => void handleDownload("pdf")} disabled={loading || downloading !== null}>
            {downloading === "pdf" ? "Gerando..." : "Baixar PDF"}
          </button>
        </div>
      </section>

      <section className="reports-filters">
        <label>Data inicial<input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} max={endDate} /></label>
        <label>Data final<input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} min={startDate} /></label>
        <label>
          Unidade
          <select value={unitName} onChange={(event) => { setUnitName(event.target.value); setSectorName(""); setPrinterUuid("") }}>
            <option value="">Todas as unidades</option>
            {units.map((unit) => <option key={unit.id} value={unit.name}>{unit.name}</option>)}
          </select>
        </label>
        <label>
          Setor
          <select value={sectorName} onChange={(event) => { setSectorName(event.target.value); setPrinterUuid("") }}>
            <option value="">Todos os setores</option>
            {availableSectors.map((sector) => <option key={sector.id} value={sector.name}>{sector.name}</option>)}
          </select>
        </label>
        <label>
          Impressora
          <select value={printerUuid} onChange={(event) => setPrinterUuid(event.target.value)}>
            <option value="">Todas as impressoras</option>
            {availablePrinters.map((printer) => {
              if (!printer.uuid) return null
              return <option key={printer.uuid} value={printer.uuid}>{printer.custom_name || printer.hostname || printer.name}</option>
            })}
          </select>
        </label>
      </section>

      {error && <div className="reports-error">{error}</div>}

      <section className="reports-metrics">
        <article><span>Impressoras</span><strong>{loading ? "..." : rows.length}</strong></article>
        <article><span>Impressões no período</span><strong>{loading ? "..." : number(totalPages)}</strong></article>
        <article><span>Custo estimado</span><strong>{loading ? "..." : currency(totalCost)}</strong></article>
        <article><span>Anomalias de contador</span><strong>{loading ? "..." : number(totalAnomalies)}</strong></article>
      </section>

      <section className="reports-table-card">
        <div className="reports-table-title">
          <div><small>DETALHAMENTO</small><h3>Consumo individual das impressoras</h3></div>
          <span>{startDate} → {endDate}</span>
        </div>
        <div className="reports-table-scroll">
          <table className="reports-table reports-table-financial">
            <thead>
              <tr>
                <th>Impressora</th><th>IP</th><th>Unidade</th><th>Setor</th>
                <th>Modelo</th><th>Inicial</th><th>Final</th><th>Impressões</th>
                <th>R$/pág.</th><th>Custo estimado</th>
              </tr>
            </thead>
            <tbody>
              {!loading && rows.map((row) => (
                <tr key={row.printer_uuid}>
                  <td><strong>{row.display_name}</strong><small>{row.serial || row.hostname || "Sem identificação extra"}</small></td>
                  <td>{row.ip || "-"}</td>
                  <td>{row.unit_name || "-"}</td>
                  <td>{row.sector_name || "-"}</td>
                  <td>{modelLabel(row.manufacturer, row.model)}</td>
                  <td>{number(row.opening_page_count)}</td>
                  <td>{number(row.closing_page_count)}</td>
                  <td className="pages">{number(row.pages_printed)}</td>
                  <td className="rate">{rate(row.cost_per_page)}<small>{row.cost_source === "printer" ? "específica" : "padrão empresa"}</small></td>
                  <td className="cost">{currency(row.estimated_cost)}</td>
                </tr>
              ))}
              {!loading && rows.length === 0 && (
                <tr><td colSpan={10} className="reports-empty">Nenhum histórico encontrado para este período.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {loading && <div className="reports-loading">Carregando relatório...</div>}
      </section>
    </div>
  )
}
