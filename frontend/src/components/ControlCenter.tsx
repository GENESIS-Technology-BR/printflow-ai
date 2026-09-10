import {
  type FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";

import {
  createControlCenterClient,
  createControlCenterClientPreview,
  createControlCenterClientUser,
  getControlCenterClientUsers,
  getControlCenterOverview,
  updateControlCenterClientUserStatus,
} from "../services/api";

import type {
  ControlCenterClientCreated,
  ControlCenterClientUser,
  ControlCenterCompany,
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

  const [selectedCompany, setSelectedCompany] =
    useState<ControlCenterCompany | null>(null);
  const [clientUsers, setClientUsers] =
    useState<ControlCenterClientUser[]>([]);
  const [usersLoading, setUsersLoading] =
    useState(false);
  const [newUserName, setNewUserName] =
    useState("");
  const [newUserEmail, setNewUserEmail] =
    useState("");
  const [newUserPassword, setNewUserPassword] =
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

  async function openClientUsers(
    company: ControlCenterCompany,
  ) {
    setSelectedCompany(company);
    setUsersLoading(true);
    setError(null);

    try {
      setClientUsers(
        await getControlCenterClientUsers(
          company.uuid,
        ),
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível carregar os usuários do cliente.",
      );
    } finally {
      setUsersLoading(false);
    }
  }

  async function handleCreateUser(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!selectedCompany) return;

    setError(null);

    try {
      await createControlCenterClientUser(
        selectedCompany.uuid,
        {
          name: newUserName.trim(),
          email: newUserEmail.trim().toLowerCase(),
          password: newUserPassword,
        },
      );

      setNewUserName("");
      setNewUserEmail("");
      setNewUserPassword("");

      await openClientUsers(
        selectedCompany,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível criar o usuário.",
      );
    }
  }

  async function toggleClientUser(
    user: ControlCenterClientUser,
  ) {
    if (!selectedCompany) return;

    try {
      await updateControlCenterClientUserStatus(
        selectedCompany.uuid,
        user.id,
        !user.active,
      );

      await openClientUsers(
        selectedCompany,
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível alterar o usuário.",
      );
    }
  }

  async function previewClient(
    company: ControlCenterCompany,
  ) {
    try {
      const session =
        await createControlCenterClientPreview(
          company.uuid,
        );

      const currentToken =
        localStorage.getItem(
          "printflow_token",
        );

      if (currentToken) {
        sessionStorage.setItem(
          "printflow_platform_admin_token",
          currentToken,
        );
      }

      sessionStorage.setItem(
        "printflow_preview_company",
        session.company_name,
      );

      localStorage.setItem(
        "printflow_token",
        session.access_token,
      );

      window.location.assign("/");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível abrir a visualização do cliente.",
      );
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
            Printflow · OPERAÇÕES
          </span>

          <h1>Control Center</h1>

          <p>
            Visão central dos clientes,
            Agentes e parques monitorados.
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
          <span>Agentes online</span>
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

        <article>
          <span>Pilotos prontos</span>
          <strong>
            {data?.pilots_ready ?? "—"}
          </strong>
          <small>
            clientes em operação
          </small>
        </article>

        <article>
          <span>Clientes em atenção</span>
          <strong>
            {data?.companies_needing_attention ?? "—"}
          </strong>
          <small>
            precisam de acompanhamento
          </small>
        </article>

        <article>
          <span>Prontos comercialmente</span>
          <strong>
            {data?.companies_commercial_ready ?? "—"}
          </strong>
          <small>
            sem bloqueios operacionais
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
              Ambientes Printflow
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
            <span>Onboarding</span>
            <span>Impressoras</span>
            <span>Alertas</span>
            <span>Readiness</span>
            <span>
              Última comunicação
            </span>
            <span>Ações</span>
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
                    company.agent_communication_state === "healthy"
                      ? "cc-online"
                      : company.agent_communication_state === "stale"
                        ? "cc-warning"
                        : "cc-offline"
                  }
                >
                  {company.agent_communication_state === "healthy"
                    ? "● Online"
                    : company.agent_communication_state === "stale"
                      ? "● Ciclo atrasado"
                      : company.agent_communication_state === "never_seen"
                        ? "● Aguardando Agent"
                        : company.agent_communication_state === "inactive"
                          ? "● Inativo"
                          : "● Offline"}
                </span>

                <span>
                  <strong>
                    {company.onboarding_state === "pilot_active"
                      ? "● Piloto ativo"
                      : company.onboarding_state === "agent_connected"
                        ? "● Agent conectado"
                        : company.onboarding_state === "awaiting_agent"
                          ? "● Aguardando instalação"
                          : company.onboarding_state === "agent_attention"
                            ? "● Requer atenção"
                            : "● Inativo"}
                  </strong>
                  <small>
                    {company.onboarding_progress}% · {company.onboarding_next_action}
                  </small>
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
                  <strong>
                    {company.commercial_ready
                      ? "● Pronto"
                      : `${company.commercial_readiness_score}%`}
                  </strong>
                  <small>
                    {company.commercial_ready
                      ? "Elegível para conversão comercial"
                      : company.commercial_blockers[0] || "Revisar operação"}
                  </small>
                </span>

                <span>
                  {formatDate(
                    company.agent_last_seen,
                  )}
                </span>

                <span className="cc-row-actions">
                  <button
                    type="button"
                    onClick={() =>
                      void openClientUsers(
                        company,
                      )
                    }
                  >
                    Usuários
                  </button>

                  <button
                    type="button"
                    className="cc-preview-button"
                    onClick={() =>
                      void previewClient(
                        company,
                      )
                    }
                  >
                    Visualizar como cliente
                  </button>
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

      {selectedCompany && (
        <section className="control-center-users">
          <div className="cc-created-header">
            <div>
              <span>
                USUÁRIOS DO CLIENTE
              </span>
              <h2>
                {selectedCompany.name}
              </h2>
            </div>

            <button
              type="button"
              onClick={() => {
                setSelectedCompany(null);
                setClientUsers([]);
              }}
            >
              Fechar
            </button>
          </div>

          <form
            className="cc-user-form"
            onSubmit={handleCreateUser}
          >
            <input
              value={newUserName}
              minLength={3}
              required
              placeholder="Nome do usuário"
              onChange={(event) =>
                setNewUserName(
                  event.target.value,
                )
              }
            />

            <input
              type="email"
              value={newUserEmail}
              required
              placeholder="usuario@empresa.com.br"
              onChange={(event) =>
                setNewUserEmail(
                  event.target.value,
                )
              }
            />

            <input
              type="password"
              value={newUserPassword}
              minLength={8}
              required
              placeholder="Senha inicial"
              onChange={(event) =>
                setNewUserPassword(
                  event.target.value,
                )
              }
            />

            <button
              type="submit"
              className="cc-primary"
            >
              + Adicionar usuário
            </button>
          </form>

          <div className="cc-user-list">
            {usersLoading ? (
              <p>Carregando usuários...</p>
            ) : clientUsers.length ? (
              clientUsers.map(
                (user) => (
                  <div
                    className="cc-user-row"
                    key={user.id}
                  >
                    <span>
                      <strong>
                        {user.name}
                      </strong>
                      <small>
                        {user.email}
                      </small>
                    </span>

                    <span>
                      {user.active
                        ? "Ativo"
                        : "Inativo"}
                    </span>

                    <button
                      type="button"
                      onClick={() =>
                        void toggleClientUser(
                          user,
                        )
                      }
                    >
                      {user.active
                        ? "Desativar"
                        : "Ativar"}
                    </button>
                  </div>
                ),
              )
            ) : (
              <p>
                Nenhum usuário cadastrado.
              </p>
            )}
          </div>
        </section>
      )}
    </section>
  );
}
