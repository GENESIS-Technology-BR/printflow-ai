import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

type Theme = "light" | "dark";

const STORAGE_KEY = "printflow_theme";

const HEADER_TARGETS = [
  ".modern-dashboard-actions",
  ".control-center-actions",
  ".reports-header",
  ".agent-monitor-header",
  ".dashboard > header",
];

function readInitialTheme(): Theme {
  const current = document.documentElement.dataset.theme;
  if (current === "dark" || current === "light") return current;

  const saved = localStorage.getItem(STORAGE_KEY);
  return saved === "dark" ? "dark" : "light";
}

function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;

  const themeMeta = document.querySelector('meta[name="theme-color"]');
  themeMeta?.setAttribute("content", theme === "dark" ? "#0B1524" : "#0A6ED1");
}

function resolveHeaderTarget(): Element | null {
  for (const selector of HEADER_TARGETS) {
    const target = document.querySelector(selector);
    if (target) return target;
  }
  return null;
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);
  const [headerTarget, setHeaderTarget] = useState<Element | null>(null);

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    let currentTarget: Element | null = null;

    const resolveTarget = () => {
      const nextTarget = resolveHeaderTarget();
      if (nextTarget !== currentTarget) {
        currentTarget = nextTarget;
        setHeaderTarget(nextTarget);
      }
    };

    resolveTarget();

    const observer = new MutationObserver(resolveTarget);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, []);

  const nextTheme = theme === "light" ? "dark" : "light";
  const label = theme === "light" ? "Ativar modo escuro" : "Ativar modo claro";

  const button = (
    <button
      type="button"
      className={`pf-theme-toggle ${headerTarget ? "pf-theme-toggle-inline" : "pf-theme-toggle-floating"}`}
      aria-label={label}
      title={label}
      onClick={() => setTheme(nextTheme)}
    >
      <span className="pf-theme-toggle-icon" aria-hidden="true">
        {theme === "light" ? "☀" : "☾"}
      </span>
      <span className="pf-theme-toggle-label">
        {theme === "light" ? "Claro" : "Escuro"}
      </span>
    </button>
  );

  return headerTarget ? createPortal(button, headerTarget) : button;
}
