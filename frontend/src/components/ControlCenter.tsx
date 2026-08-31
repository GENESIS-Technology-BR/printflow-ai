import {
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  getControlCenterOverview,
} from "../services/api";

import type {
  ControlCenterOverview,
} from "../services/api";

import { parseApiDate } from "../utils/dateTime";

import "./ControlCenter.css";


function formatDate(
  value: string | null,
): string {
  if (!value) return "Sem comunicação";

  const date = parseApiDate(value);

  if (Number.isNaN(date.getTime())) {
    return "Data indisponível";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "short",
    },
  ).format(date);
}


export default function ControlCenter() {
  const [data, setData] =
    useState<ControlCenterOverview | null>(
      null,
    );

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(
        await getControlCenterOverview(),
      );

      setError(null);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Falha ao carregar Control Center",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();

    const interval = window.setInterval(
      () => void load(),
      30_000,
    );

    return () =>
      window.clearInterval(interval);
  }, [load]);

  return (
    <section className="control-center-page">
      <header className="control-center-header">
        <div>
          <span>PRINTFLOW · OPERAÇÕES</span>

          <h1>Control Center</h1>

          <p>
            Visão central dos clientes,
            Agents e parques monitorados.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void load()}
        >
          Atualizar
        </button>
      </header>

      {error && (
        <div className="control-center-error">
          {error}
        </div>
      )}

      <div className="control-center-kpis">
        <article>
          <span>Clientes</span>
          <strong>
            {data?.companies_total ?? "—"}
          </strong>
          <small>empresas cadastradas</small>
        </article>

        <article>
          <span>Agents online</span>
          <strong>
            {data?.agents_online ?? "—"}
          </strong>
          <small>com comunicação recente</small>
        </article>

        <article>
          <span>Impressoras</span>
          <strong>
            {data?.active_printers ?? "—"}
          </strong>
          <small>ativas monitoradas</small>
        </article>

        <article>
          <span>Alertas</span>
          <strong>
            {data?.open_alerts ?? "—"}
          </strong>
          <small>requerem atenção</small>
        </article>
      </div>

      <section className="control-center-panel">
        <div className="control-center-title">
          <div>
            <span>CLIENTES MONITORADOS</span>
            <h2>Ambientes PRINTFLOW</h2>
          </div>

          <small>
            {loading
              ? "Atualizando..."
              : `${data?.companies_active ?? 0} ativos`}
          </small>
        </div>

        <div className="control-center-table">
          <div className="control-center-row header">
            <span>Empresa</span>
            <span>Agent</span>
            <span>Versão</span>
            <span>Impressoras</span>
            <span>Alertas</span>
            <span>Última comunicação</span>
          </div>

          {data?.companies.map(
            (company) => (
              <div
                className="control-center-row"
                key={company.uuid}
              >
                <span>
                  <strong>
                    {company.name}
                  </strong>
                  <small>
                    Plano {company.plan}
                  </small>
                </span>

                <span
                  className={
                    company.agent_online
                      ? "cc-online"
                      : "cc-offline"
                  }
                >
                  {company.agent_online
                    ? "● Online"
                    : "● Offline"}
                </span>

                <span>
                  {company.agent_version
                    ? `v${company.agent_version}`
                    : "—"}
                </span>

                <span>
                  {company.active_printers}
                </span>

                <span>
                  {company.alerts}
                </span>

                <span>
                  {formatDate(
                    company.agent_last_seen,
                  )}
                </span>
              </div>
            ),
          )}

          {!loading &&
            !data?.companies.length && (
              <div className="control-center-empty">
                Nenhum cliente cadastrado.
              </div>
            )}
        </div>
      </section>
    </section>
  );
}
