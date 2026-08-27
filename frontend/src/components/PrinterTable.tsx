import {
  useState,
} from "react";

import type {
  DashboardPrinter,
} from "../services/api";

import {
  updatePrinterCustomName,
} from "../services/api";

import { parseApiDate } from "../utils/dateTime";

type PrinterTableProps = {
  printers: DashboardPrinter[];
};

function formatPages(value: number | null): string {
  if (value === null) {
    return "Não disponível";
  }

  return new Intl.NumberFormat(
    "pt-BR",
  ).format(value);
}

function formatLastSeen(
  value: string | null,
): string {
  if (!value) {
    return "Sem comunicação";
  }

  const date = parseApiDate(value);

  if (Number.isNaN(date.getTime())) {
    return "Não informado";
  }

  return new Intl.DateTimeFormat(
    "pt-BR",
    {
      dateStyle: "short",
      timeStyle: "short",
    },
  ).format(date);
}

function getStatusLabel(status: string): string {
  const normalized = status.toLowerCase();

  if (normalized === "online") {
    return "Online";
  }

  if (normalized === "offline") {
    return "Offline";
  }

  return "Desconhecido";
}

export default function PrinterTable({
  printers,
}: PrinterTableProps) {
  const [draftNames, setDraftNames] =
    useState<Record<string, string>>({});

  const [savedNames, setSavedNames] =
    useState<Record<string, string | null>>({});

  const [savingUuid, setSavingUuid] =
    useState<string | null>(null);

  const [saveError, setSaveError] =
    useState<string | null>(null);

  function currentCustomName(
    printer: DashboardPrinter,
  ): string {
    const key = printer.uuid;

    if (!key) {
      return printer.custom_name || "";
    }

    if (draftNames[key] !== undefined) {
      return draftNames[key];
    }

    if (savedNames[key] !== undefined) {
      return savedNames[key] || "";
    }

    return printer.custom_name || "";
  }

  async function saveCustomName(
    printer: DashboardPrinter,
  ): Promise<void> {
    if (!printer.uuid) {
      setSaveError(
        "Esta impressora ainda não possui identificador para edição.",
      );
      return;
    }

    const value = currentCustomName(
      printer,
    ).trim();

    try {
      setSavingUuid(printer.uuid);
      setSaveError(null);

      const result =
        await updatePrinterCustomName(
          printer.uuid,
          value || null,
        );

      setSavedNames((current) => ({
        ...current,
        [printer.uuid as string]:
          result.custom_name,
      }));

      setDraftNames((current) => ({
        ...current,
        [printer.uuid as string]:
          result.custom_name || "",
      }));
    } catch (error) {
      setSaveError(
        error instanceof Error
          ? error.message
          : "Falha ao salvar o nome personalizado.",
      );
    } finally {
      setSavingUuid(null);
    }
  }

  if (!printers.length) {
    return (
      <div className="dashboard-empty">
        <span>🖨️</span>

        <h3>Nenhuma impressora cadastrada</h3>

        <p>
          Instale o PRINTFLOW Agent na rede para
          iniciar a descoberta dos equipamentos.
        </p>
      </div>
    );
  }

  return (
    <div className="printer-cards">
      {saveError && (
        <div className="printer-alias-error">
          {saveError}
        </div>
      )}

      {printers.map((printer) => (
        <article
          className="printer-card"
          key={
            printer.uuid ||
            printer.id ||
            printer.ip ||
            printer.name
          }
        >
          <div className="printer-card-main">
            <div className="printer-identity">
              <span className="printer-icon">
                🖨️
              </span>

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
                      aria-label={`Nome personalizado de ${printer.name}`}
                      onChange={(event) => {
                        if (!printer.uuid) {
                          return;
                        }

                        setDraftNames((current) => ({
                          ...current,
                          [printer.uuid as string]:
                            event.target.value,
                        }));
                      }}
                    />

                    <button
                      type="submit"
                      disabled={
                        !printer.uuid ||
                        savingUuid === printer.uuid
                      }
                    >
                      {savingUuid === printer.uuid
                        ? "Salvando..."
                        : "Salvar"}
                    </button>
                  </form>
                </div>

                <span>
                  {printer.manufacturer ||
                    "Fabricante não identificado"}
                  {printer.model
                    ? ` • ${printer.model}`
                    : ""}
                </span>

                <small className="printer-hostname">
                  Host: {printer.hostname || "Não identificado"}
                </small>

                <small>
                  Origem: {printer.source || "Não informada"}
                </small>
              </div>
            </div>

            <div className="printer-connection">
              <code>
                {printer.ip || "Não informado"}
              </code>

              <span
                className={`status-pill status-${printer.status}`}
              >
                <i />
                {getStatusLabel(printer.status)}
              </span>
            </div>

            <div className="health-cell">
              <strong>
                {printer.health_score}%
              </strong>

              <div className="health-bar">
                <span
                  style={{
                    width:
                      `${printer.health_score}%`,
                  }}
                />
              </div>
            </div>
          </div>

          <div className="printer-card-details">
            <div className="printer-detail">
              <span>Serial</span>
              <strong>
                {printer.serial || "Não disponível"}
              </strong>

              {printer.serial_confidence !== null && (
                <small>
                  {` ${printer.serial_confidence}%`}
                  {printer.serial_confirmed
                    ? " • confirmado"
                    : ""}
                </small>
              )}
            </div>

            <div className="printer-detail">
              <span>Páginas</span>
              <strong>
                {formatPages(printer.page_count)}
              </strong>

              {printer.page_count_confidence !== null && (
                <small>
                  {`${printer.page_count_confidence}% de confiança`}
                </small>
              )}
            </div>

            <div className="printer-detail">
              <span>Toner</span>
              <strong>
                {printer.toner_percent === null
                  ? "Não disponível"
                  : `${printer.toner_percent}%`}
              </strong>
            </div>

            <div className="printer-detail">
              <span>Última comunicação</span>
              <strong>
                {formatLastSeen(printer.last_seen)}
              </strong>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
