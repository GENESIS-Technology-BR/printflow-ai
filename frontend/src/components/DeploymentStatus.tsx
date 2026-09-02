import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

import "./DeploymentStatus.css";

type WorkflowRun = {
  run_number: number;
  status: "queued" | "in_progress" | "completed" | string;
  conclusion: "success" | "failure" | "cancelled" | "timed_out" | null | string;
  head_sha: string;
  updated_at: string;
};

type WorkflowResponse = {
  workflow_runs?: WorkflowRun[];
};

function statusLabel(run: WorkflowRun | null): {
  tone: "loading" | "success" | "warning" | "error";
  label: string;
} {
  if (!run) return { tone: "loading", label: "Consultando" };
  if (run.status !== "completed") return { tone: "warning", label: "Em andamento" };
  if (run.conclusion === "success") return { tone: "success", label: "Pronto" };
  return { tone: "error", label: "Falhou" };
}

export default function DeploymentStatus() {
  const [target, setTarget] = useState<HTMLElement | null>(null);
  const [run, setRun] = useState<WorkflowRun | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    const aside = document.querySelector(".shell > aside") as HTMLElement | null;
    setTarget(aside);
  }, []);

  useEffect(() => {
    let active = true;

    async function load(): Promise<void> {
      try {
        const response = await fetch(
          "https://api.github.com/repos/GENESIS-Technology-BR/printflow-ai/actions/runs?branch=main&per_page=1",
          {
            headers: {
              Accept: "application/vnd.github+json",
            },
          },
        );
        if (!response.ok) throw new Error("status indisponível");
        const data = (await response.json()) as WorkflowResponse;
        if (!active) return;
        setRun(data.workflow_runs?.[0] || null);
        setUnavailable(false);
      } catch {
        if (!active) return;
        setUnavailable(true);
      }
    }

    void load();
    const interval = window.setInterval(() => void load(), 300_000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, []);

  if (!target) return null;

  const display = statusLabel(run);
  const build = run ? `#${run.run_number}` : "—";
  const commit = run?.head_sha ? run.head_sha.slice(0, 7) : "—";

  return createPortal(
    <div className="deployment-status" aria-live="polite">
      <span className="deployment-status-title">Atualização do sistema</span>
      <div className={`deployment-status-state deployment-${unavailable ? "loading" : display.tone}`}>
        <i />
        <strong>{unavailable ? "Indisponível" : display.label}</strong>
      </div>
      <small>Build {build} · {commit}</small>
    </div>,
    target,
  );
}
