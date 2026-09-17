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
type PeriodPreset = 7 | 30 | 90

function inputDate(date: Date): string {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return local.toISOString().slice(0, 10)
}
function number(value: number | null): string { if (value === null) return "-"; return new Intl.NumberFormat("pt-BR").format(value) }
function currency(value: number): string { return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value) }
function rate(value: number): string { return `R$ ${Number(value || 0).toFixed(4).replace(".", ",")}` }
function modelLabel(manufacturer: string | null, model: string | null): string { const brand=(manufacturer||"").trim(),modelText=(model||"").trim(); if(!modelText)return brand||"-"; if(brand&&modelText.toLowerCase().startsWith(brand.toLowerCase()))return modelText; return[brand,modelText].filter(Boolean).join(" ")||"-" }
function dateLabel(value:string):string{const[year,month,day]=value.split("-");if(!year||!month||!day)return value;return`${day}/${month}/${year}`}
function isLabelPrinter(row:UsageReportRow):boolean{const text=`${row.manufacturer||""} ${row.model||""} ${row.display_name||""}`.toLowerCase();return text.includes("zebra")||text.includes("zt230")||text.includes("zpl")}

export default function Reports({companyName}:ReportsProps){
 const today=useMemo(()=>new Date(),[]);const initialStart=useMemo(()=>{const start=new Date(today);start.setDate(start.getDate()-29);return start},[today]);
 const[startDate,setStartDate]=useState(inputDate(initialStart)),[endDate,setEndDate]=useState(inputDate(today)),[unitName,setUnitName]=useState(""),[sectorName,setSectorName]=useState(""),[printerUuid,setPrinterUuid]=useState("");
 const[units,setUnits]=useState<OrganizationUnit[]>([]),[sectors,setSectors]=useState<OrganizationSector[]>([]),[printers,setPrinters]=useState<DashboardPrinter[]>([]),[rows,setRows]=useState<UsageReportRow[]>([]),[loading,setLoading]=useState(true),[downloading,setDownloading]=useState<"xlsx"|"pdf"|null>(null),[error,setError]=useState<string|null>(null);
 const filters=useMemo<UsageReportFilters>(()=>({startDate,endDate,unitName:unitName||undefined,sectorName:sectorName||undefined,printerUuid:printerUuid||undefined}),[startDate,endDate,unitName,sectorName,printerUuid]);
 useEffect(()=>{let cancelled=false;async function loadCatalogs(){try{const[u,s,p]=await Promise.all([getOrganizationUnits(),getOrganizationSectors(),getDashboardPrinters()]);if(cancelled)return;setUnits(u);setSectors(s);setPrinters(p)}catch{if(!cancelled)setError("Não foi possível carregar os filtros do relatório.")}}void loadCatalogs();return()=>{cancelled=true}},[]);
 useEffect(()=>{let cancelled=false;async function loadReport(){setLoading(true);setError(null);try{const data=await getUsageReport(filters);if(!cancelled)setRows(data)}catch(e){if(!cancelled){setRows([]);setError(e instanceof Error?e.message:"Não foi possível carregar o relatório.")}}finally{if(!cancelled)setLoading(false)}}void loadReport();return()=>{cancelled=true}},[filters]);
 const selectedUnit=units.find(u=>u.name===unitName);const availableSectors=selectedUnit?sectors.filter(s=>s.unit_id===selectedUnit.id):sectors;const availablePrinters=printers.filter(p=>(!unitName||p.unit_name===unitName)&&(!sectorName||p.sector_name===sectorName));
 const totalPages=rows.reduce((t,r)=>t+r.pages_printed,0),totalAnomalies=rows.reduce((t,r)=>t+r.anomaly_count,0),totalCost=rows.reduce((t,r)=>t+r.estimated_cost,0),averageCost=totalPages>0?totalCost/totalPages:0;
 const selectedPrinter=printers.find(p=>p.uuid===printerUuid);const activeScope=[unitName?`Unidade: ${unitName}`:null,sectorName?`Setor: ${sectorName}`:null,selectedPrinter?`Impressora: ${selectedPrinter.custom_name||selectedPrinter.hostname||selectedPrinter.name}`:null].filter(Boolean);
 function applyPeriod(days:PeriodPreset){const end=new Date(),start=new Date(end);start.setDate(start.getDate()-(days-1));setStartDate(inputDate(start));setEndDate(inputDate(end))}function clearScope(){setUnitName("");setSectorName("");setPrinterUuid("")}
 async function handleDownload(format:"xlsx"|"pdf"){setDownloading(format);setError(null);try{const blob=await downloadUsageReport(format,filters),objectUrl=URL.createObjectURL(blob),link=document.createElement("a");link.href=objectUrl;link.download=`printflow-${startDate}-${endDate}.${format}`;document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(objectUrl)}catch(e){setError(e instanceof Error?e.message:"Não foi possível baixar o relatório.")}finally{setDownloading(null)}}
 return <div className="reports-page">
  <header className="reports-header"><div><small>GESTÃO DE CONSUMO E CUSTOS</small><h1>Relatórios</h1><p>{companyName}</p></div><span className="online">● Histórico ativo</span></header>
  <section className="reports-intro"><div><small>Printflow · FECHAMENTO COMERCIAL</small><h2>Consumo individual do parque</h2><p>Fechamento por equipamento com contadores, volume, tarifa e custo estimado, pronto para Excel ou PDF.</p></div><div className="reports-downloads"><button type="button" onClick={()=>void handleDownload("xlsx")} disabled={loading||downloading!==null}>{downloading==="xlsx"?"Gerando...":"Exportar Excel"}</button><button type="button" className="pdf" onClick={()=>void handleDownload("pdf")} disabled={loading||downloading!==null}>{downloading==="pdf"?"Gerando...":"Exportar PDF"}</button></div></section>
  <section className="reports-period-bar" aria-label="Períodos rápidos"><div><span>Período rápido</span><button type="button" onClick={()=>applyPeriod(7)}>7 dias</button><button type="button" onClick={()=>applyPeriod(30)}>30 dias</button><button type="button" onClick={()=>applyPeriod(90)}>90 dias</button></div><strong>{dateLabel(startDate)} → {dateLabel(endDate)}</strong></section>
  <section className="reports-filters"><label>Data inicial<input type="date" value={startDate} onChange={e=>setStartDate(e.target.value)} max={endDate}/></label><label>Data final<input type="date" value={endDate} onChange={e=>setEndDate(e.target.value)} min={startDate}/></label><label>Unidade<select value={unitName} onChange={e=>{setUnitName(e.target.value);setSectorName("");setPrinterUuid("")}}><option value="">Todas as unidades</option>{units.map(u=><option key={u.id} value={u.name}>{u.name}</option>)}</select></label><label>Setor<select value={sectorName} onChange={e=>{setSectorName(e.target.value);setPrinterUuid("")}}><option value="">Todos os setores</option>{availableSectors.map(s=><option key={s.id} value={s.name}>{s.name}</option>)}</select></label><label>Impressora<select value={printerUuid} onChange={e=>setPrinterUuid(e.target.value)}><option value="">Todas as impressoras</option>{availablePrinters.map(p=>p.uuid?<option key={p.uuid} value={p.uuid}>{p.custom_name||p.hostname||p.name}</option>:null)}</select></label></section>
  <section className="reports-scope-bar"><div><span>Escopo</span><strong>{activeScope.length?activeScope.join(" · "):"Parque completo"}</strong></div>{activeScope.length>0&&<button type="button" onClick={clearScope}>Limpar filtros</button>}</section>{error&&<div className="reports-error">{error}</div>}
  <section className="reports-metrics"><article><span>Impressoras no fechamento</span><strong>{loading?"...":rows.length}</strong></article><article><span>Impressões no período</span><strong>{loading?"...":number(totalPages)}</strong></article><article><span>Custo estimado</span><strong>{loading?"...":currency(totalCost)}</strong></article><article><span>Custo médio/página</span><strong>{loading?"...":rate(averageCost)}</strong></article></section>
  <section className="reports-table-card"><div className="reports-table-title"><div><small>DETALHAMENTO POR EQUIPAMENTO</small><h3>Fechamento individual das impressoras</h3></div><span>{rows.length} item(ns) · {totalAnomalies} anomalia(s)</span></div><div className="reports-table-scroll"><table className="reports-table reports-table-financial"><thead><tr><th>Impressora</th><th>IP</th><th>Unidade</th><th>Setor</th><th>Modelo</th><th>Inicial</th><th>Final</th><th>Impressões</th><th>R$/pág.</th><th>Custo estimado</th></tr></thead><tbody>{!loading&&rows.map(row=>{const label=isLabelPrinter(row);return <tr key={row.printer_uuid}><td><strong>{row.display_name}</strong><small>{row.serial||row.hostname||"Sem identificação extra"}</small></td><td>{row.ip||"-"}</td><td>{row.unit_name||"-"}</td><td>{row.sector_name||"-"}</td><td>{modelLabel(row.manufacturer,row.model)}</td><td>{number(row.opening_page_count)}</td><td>{number(row.closing_page_count)}</td><td className="pages">{label?"N/A":number(row.pages_printed)}</td><td className="rate">{label?"N/A":rate(row.cost_per_page)}<small>{label?"impressora de etiquetas":row.cost_source==="printer"?"específica":"padrão empresa"}</small></td><td className="cost">{label?"Não aplicável":currency(row.estimated_cost)}</td></tr>})}{!loading&&rows.length===0&&<tr><td colSpan={10} className="reports-empty">Nenhum histórico encontrado para este período.</td></tr>}</tbody></table></div>{loading&&<div className="reports-loading">Carregando relatório...</div>}</section>
 </div>
}
