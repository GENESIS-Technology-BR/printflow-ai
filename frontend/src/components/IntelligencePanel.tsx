import { useCallback, useEffect, useState } from "react";

import { API_BASE_URL } from "../services/api";
import "./IntelligencePanel.css";

type IntelligenceSeverity = "critical" | "warning" | "opportunity" | "info";

type IntelligenceFinding = {
  id: string;
  category: string;
  severity: IntelligenceSeverity;
  title: string;
  problem: string;
  impact: string;
  recommendation: string;
  printer_uuid: string | null;
  printer_name: string | null;
  unit_name: string | null;
  sector_name: string | null;
  confidence: number;
};

type IntelligenceOverview = {
  engine: string;
  generated_at: string;
  score: number;
  headline: string;
  attention_count: number;
  counts: Record<IntelligenceSeverity, number>;
  findings: IntelligenceFinding[];
  analysis_window_days: number;
};

type IntelligencePanelProps = {
  refreshKey?: number;
  onOpenPrinters: () => void;
};

function severityLabel(severity: IntelligenceSeverity): string {
  if (severity === "critical") return "Crítico";
  if (severity === "warning") return "Atenção";
  if (severity === "opportunity") return "Oportunidade";
  return "Informação";
}

export default function IntelligencePanel({
  refreshKey = 0,
  onOpenPrinters,
}: IntelligencePanelProps) {
  const [overview, setOverview] = useState<IntelligenceOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = localStorage.getItem("printflow_token");
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/intelligence/overview`, {
        headers: {
          Accept: "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setOverview((await response.json()) as IntelligenceOverview);
      setError(null);
    } catch {
      setError("Não foi possível gerar a análise inteligente agora.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    void load();
    const intervalId = window.setInterval(() => void load(), 60_000);
    return () => window.clearInterval(intervalId);
  }, [load, refreshKey]);

  if (loading && !overview) {
    return (
      <section className="pf-intelligence-panel pf-intelligence-loading">
        <strong>Printflow Intelligence</strong>
        <span>Analisando o parque e procurando desvios...</span>
      </section>
    );
  }

  if (error && !overview) {
    return (
      <section className="pf-intelligence-panel pf-intelligence-error">
        <strong>Printflow Intelligence</strong>
        <span>{error}</span>
      </section>
    );
  }

  if (!overview) return null;

  const featured = overview.findings.slice(0, 4);

  return (
    <section className="pf-intelligence-panel">
      <header className="pf-intelligence-header">
        <div className="pf-intelligence-heading">
          <img src="/brand/printflow-mark.svg" alt="" aria-hidden="true" />
          <div>
            <span>PRINTFLOW INTELLIGENCE · v0.5.0</span>
            <h2>O que precisa da sua atenção hoje?</h2>
            <p>{overview.headline}</p>
          </div>
        </div>

        <div className="pf-intelligence-score" title="Índice calculado por regras operacionais do Printflow">
          <span>Índice</span>
          <strong>{overview.score}</strong>
          <small>/100</small>
        </div>
      </header>

      <div className="pf-intelligence-summary">
        <span className="critical"><b>{overview.counts.critical}</b> críticos</span>
        <span className="warning"><b>{overview.counts.warning}</b> atenção</span>
        <span className="opportunity"><b>{overview.counts.opportunity}</b> oportunidades</span>
        <small>Análise automática dos últimos {overview.analysis_window_days} dias · sem IA externa</small>
      </div>

      {featured.length ? (
        <div className="pf-intelligence-list">
          {featured.map((finding) => (
            <article className={`pf-intelligence-item severity-${finding.severity}`} key={finding.id}>
              <div className="pf-intelligence-item-top">
                <span>{severityLabel(finding.severity)}</span>
                <small>{Math.round(finding.confidence * 100)}% confiança</small>
              </div>
              <h3>{finding.title}</h3>
              <p><b>Problema:</b> {finding.problem}</p>
              <p><b>Impacto:</b> {finding.impact}</p>
              <div className="pf-intelligence-action">
                <strong>Recomendação</strong>
                <span>{finding.recommendation}</span>
              </div>
              {(finding.unit_name || finding.sector_name) && (
                <small className="pf-intelligence-location">
                  {[finding.unit_name, finding.sector_name].filter(Boolean).join(" · ")}
                </small>
              )}
            </article>
          ))}
        </div>
      ) : (
        <div className="pf-intelligence-clear">
          <strong>✓ Ambiente sem desvios relevantes</strong>
          <span>O Printflow continuará analisando saúde, comunicação, contadores e comportamento de volume.</span>
        </div>
      )}

      {overview.findings.length > featured.length && (
        <button type="button" className="pf-intelligence-more" onClick={onOpenPrinters}>
          Ver equipamentos relacionados ({overview.findings.length}) →
        </button>
      )}
    </section>
  );
}
