import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  createControlCenterClient,
  getControlCenterOverview,
} from "../services/api";

import type {
  ControlCenterClientCreated,
  ControlCenterOverview,
} from "../services/api";

import {
  parseApiDate,
} from "../utils/dateTime";

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

  const [showCreate, setShowCreate] =
    useState(false);

  const [creating, setCreating] =
    useState(false);

  const [companyName, setCompanyName] =
    useState("");

  const [
    responsibleName,
    setResponsibleName,
  ] = useState("");

  const [email, setEmail] =
    useState("");

  const [
    createdClient,
    setCreatedClient,
  ] =
    useState<ControlCenterClientCreated | null>(
      null,
    );

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

  async function handleCreateClient(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setCreating(true);
    setError(null);

    try {
      const created =
        await createControlCenterClient({
          company_name:
            companyName.trim(),
          responsible_name:
            responsibleName.trim(),
          email:
            email.trim().toLowerCase(),
        });

      setCreatedClient(created);

      setCompanyName("");
      setResponsibleName("");
      setEmail("");
      setShowCreate(false);

      await load();

    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível criar o cliente.",
      );
    } finally {
      setCreating(false);
    }
  }

  async function copyValue(
    value: string,
  ) {
    try {
      await navigator.clipboard.writeText(
        value,
      );
    } catch {
      setError(
        "Não foi possível copiar automaticamente.",
      );
    }
  }

  return (
    <section className="control-center-page">
      <header className="control-center-header">
        <div>
          <span>
            PRINTFLOW · OPERAÇÕES
          </span>

          <h1>Control Center</h1>

          <p>
            Visão central dos clientes,
            Agents e parques monitorados.
          </p>
        </div>

        <div className="control-center-actions">
          <button
            type="button"
            className="cc-primary"
            onClick={() => {
              setShowCreate(
                (current) => !current,
              );
            }}
          >
            {showCreate
              ? "Cancelar"
              : "+ Novo cliente"}
          </button>

          <button
            type="button"
            onClick={() => void load()}
          >
            Atualizar
          </button>
        </div>
      </header>

      {error && (
        <div className="control-center-error">
          {error}
        </div>
      )}

      {showCreate && (
        <section className="control-center-onboarding">
          <div className="cc-onboarding-intro">
            <span>ONBOARDING</span>

            <h2>Novo cliente</h2>

            <p>
              Crie a empresa, o usuário
              administrador e o token do Agent
              em uma única etapa.
            </p>
          </div>

          <form
            className="cc-onboarding-form"
            onSubmit={handleCreateClient}
          >
            <label>
              Empresa

              <input
                type="text"
                value={companyName}
                minLength={2}
                maxLength={180}
                required
                placeholder="Ex.: Empresa ABC"
                onChange={(event) =>
                  setCompanyName(
                    event.target.value,
                  )
                }
              />
            </label>

            <label>
              Responsável

              <input
                type="text"
                value={responsibleName}
                minLength={3}
                maxLength={120}
                required
                placeholder="Ex.: João Silva"
                onChange={(event) =>
                  setResponsibleName(
                    event.target.value,
                  )
                }
              />
            </label>

            <label>
              E-mail

              <input
                type="email"
                value={email}
                required
                placeholder="joao@empresa.com.br"
                onChange={(event) =>
                  setEmail(
                    event.target.value,
                  )
                }
              />
            </label>

            <button
              type="submit"
              className="cc-create-button"
              disabled={creating}
            >
              {creating
                ? "Criando..."
                : "Criar cliente"}
            </button>
          </form>
        </section>
      )}

      {createdClient && (
        <section className="control-center-created">
          <div className="cc-created-header">
            <div>
              <span>
                CLIENTE CRIADO COM SUCESSO
              </span>

              <h2>
                {createdClient.company_name}
              </h2>
            </div>

            <button
              type="button"
              onClick={() =>
                setCreatedClient(null)
              }
            >
              Fechar
            </button>
          </div>

          <p className="cc-created-warning">
            Copie os dados abaixo agora.
            A senha temporária não será
            exibida novamente depois que
            esta tela for recarregada.
          </p>

          <div className="cc-created-grid">
            <div>
              <span>Login</span>

              <div className="cc-secret-row">
                <code>
                  {createdClient.email}
                </code>

                <button
                  type="button"
                  onClick={() =>
                    void copyValue(
                      createdClient.email,
                    )
                  }
                >
                  Copiar
                </button>
              </div>
            </div>

            <div>
              <span>Senha temporária</span>

              <div className="cc-secret-row">
                <code>
                  {
                    createdClient
                      .temporary_password
                  }
                </code>

                <button
                  type="button"
                  onClick={() =>
                    void copyValue(
                      createdClient
                        .temporary_password,
                    )
                  }
                >
                  Copiar
                </button>
              </div>
            </div>

            <div className="cc-token-field">
              <span>Token do Agent</span>

              <div className="cc-secret-row">
                <code>
                  {createdClient.agent_token}
                </code>

                <button
                  type="button"
                  onClick={() =>
                    void copyValue(
                      createdClient.agent_token,
                    )
                  }
                >
                  Copiar
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      <div className="control-center-kpis">
        <article>
          <span>Clientes</span>
          <strong>
            {data?.companies_total ?? "—"}
          </strong>
          <small>
            empresas cadastradas
          </small>
        </article>

        <article>
          <span>Agents online</span>
          <strong>
            {data?.agents_online ?? "—"}
          </strong>
          <small>
            com comunicação recente
          </small>
        </article>

        <article>
          <span>Impressoras</span>
          <strong>
            {data?.active_printers ?? "—"}
          </strong>
          <small>
            ativas monitoradas
          </small>
        </article>

        <article>
          <span>Alertas</span>
          <strong>
            {data?.open_alerts ?? "—"}
          </strong>
          <small>
            requerem atenção
          </small>
        </article>
      </div>

      <section className="control-center-panel">
        <div className="control-center-title">
          <div>
            <span>
              CLIENTES MONITORADOS
            </span>

            <h2>
              Ambientes PRINTFLOW
            </h2>
          </div>

          <small>
            {loading
              ? "Atualizando..."
              : `${
                  data?.companies_active ?? 0
                } ativos`}
          </small>
        </div>

        <div className="control-center-table">
          <div className="control-center-row header">
            <span>Empresa</span>
            <span>Agent</span>
            <span>Versão</span>
            <span>Impressoras</span>
            <span>Alertas</span>
            <span>
              Última comunicação
            </span>
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
                  {
                    company
                      .active_printers
                  }
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
