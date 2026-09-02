import { useCallback, useEffect, useMemo, useState } from "react";

import { getDashboardSummary } from "../services/api";
import type { DashboardSummary } from "../services/api";

import { parseApiDate } from "../utils/dateTime";

import "./AgentMonitor.css";

type AgentMonitorProps = {
  agentToken: string | null;
  onRegenerateToken: () => void;
};

function formatDate(value: string | null): string {
  if (!value) return "Ainda não comunicado";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "Data indisponível";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(date);
}

function formatElapsed(value: string | null): string {
  if (!value) return "Sem histórico";
  const elapsed = Math.max(0, Date.now() - parseApiDate(value).getTime());
  const minutes = Math.floor(elapsed / 60_000);
  if (minutes < 1) return "Agora";
  if (minutes < 60) return `Há ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Há ${hours} h`;
  return `Há ${Math.floor(hours / 24)} dia(s)`;
}

function formatTechnicalStatus(value: string | null | undefined): string {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "running") return "Em execução";
  if (normalized === "error") return "Com erro";
  if (normalized === "offline") return "Offline";
  if (normalized === "online") return "Online";
  return value || "Aguardando";
}

export default function AgentMonitor({
  agentToken,
  onRegenerateToken,
}: AgentMonitorProps) {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const loadAgent = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      setSummary(await getDashboardSummary());
      setError(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível consultar o Agent.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadAgent();
    const interval = window.setInterval(() => void loadAgent(), 30_000);
    return () => window.clearInterval(interval);
  }, [loadAgent]);

  const agent = summary?.agent;
  const protectedToken = agentToken
    ? `•••••••••••••••••••••••••••••••••••••••${agentToken.slice(-4)}`
    : "Token não disponível";
  const state = useMemo(() => {
    if (!agent?.last_seen) {
      return {
        tone: "waiting",
        label: "Aguardando instalação",
        message: "Nenhum Agent comunicou com esta empresa.",
      };
    }
    if (!agent.online) {
      return {
        tone: "offline",
        label: "Sem comunicação",
        message: "O Agent não envia dados há mais de 30 minutos.",
      };
    }
    if (agent.status === "error" || agent.last_error) {
      return {
        tone: "warning",
        label: "Requer atenção",
        message: agent.last_error || "O último ciclo terminou com erro.",
      };
    }
    return {
      tone: "online",
      label: "Operação normal",
      message: "Agent conectado e realizando ciclos automaticamente.",
    };
  }, [agent]);

  async function copyToken() {
    if (!agentToken) return;
    await navigator.clipboard.writeText(agentToken);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2500);
  }

  return (
    <section className="agent-monitor-page">
      <header className="agent-monitor-header">
        <div>
          <span>MONITORAMENTO OPERACIONAL</span>
          <h1>Agentes</h1>
          <p>Estado da coleta, comunicação e versão instalada.</p>
        </div>
        <button type="button" onClick={() => void loadAgent(true)} disabled={refreshing}>
          {refreshing ? "Atualizando..." : "Atualizar agora"}
        </button>
      </header>

      {error && <div className="agent-monitor-error">{error}</div>}

      <article className={`agent-overview agent-${state.tone}`}>
        <div className="agent-state-icon"><i /></div>
        <div className="agent-state-copy">
          <span>ESTADO DO AGENT</span>
          <h2>{loading ? "Consultando..." : state.label}</h2>
          <p>{state.message}</p>
        </div>
        <div className="agent-state-time">
          <strong>{formatElapsed(agent?.last_seen || null)}</strong>
          <span>última comunicação</span>
        </div>
      </article>

      <div className="agent-metrics">
        <article>
          <span>Nome</span>
          <strong>{agent?.name || "Printflow Agent"}</strong>
          <small>Identificação registrada</small>
        </article>
        <article>
          <span>Versão instalada</span>
          <strong>{agent?.version ? `v${agent.version}` : "Não informada"}</strong>
          <small>Versão reportada no heartbeat</small>
        </article>
        <article>
          <span>Último ciclo</span>
          <strong>{formatDate(agent?.last_seen || null)}</strong>
          <small>Coleta do Agent a cada 5 min • tela atualizada a cada 30 s</small>
        </article>
        <article>
          <span>Status técnico</span>
          <strong>{formatTechnicalStatus(agent?.status)}</strong>
          <small>{summary ? `${summary.active_printers} impressora(s) monitorada(s)` : "Carregando frota"}</small>
        </article>
      </div>

      <div className="agent-monitor-grid">
        <article className="agent-panel">
          <div className="agent-panel-title">
            <div>
              <span>ALERTAS</span>
              <h3>Diagnóstico operacional</h3>
            </div>
          </div>
          <div className={`agent-alert agent-alert-${state.tone}`}>
            <i />
            <div>
              <strong>{state.label}</strong>
              <p>{state.message}</p>
            </div>
          </div>
          {agent?.last_error && (
            <div className="agent-error-detail">
              <strong>Último erro registrado</strong>
              <code>{agent.last_error}</code>
            </div>
          )}
        </article>

        <article className="agent-panel">
          <div className="agent-panel-title">
            <div>
              <span>VINCULAÇÃO</span>
              <h3>Token do Agent</h3>
            </div>
          </div>
          <p className="agent-token-help">
            O token fica protegido na tela. Use “Copiar token” durante a instalação.
          </p>
          <code className="agent-token">
            {protectedToken}
          </code>
          <div className="agent-actions">
            <button type="button" onClick={() => void copyToken()} disabled={!agentToken}>
              {copied ? "Token copiado" : "Copiar token"}
            </button>
            <button type="button" className="agent-danger" onClick={onRegenerateToken}>
              Gerar novo
            </button>
          </div>
        </article>
      </div>
    </section>
  );
}
