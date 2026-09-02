import { useEffect, useState } from "react";
import { createPortal } from "react-dom";

type Theme = "light" | "dark";

const STORAGE_KEY = "printflow_theme";

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

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);
  const [headerTarget, setHeaderTarget] = useState<Element | null>(null);

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  useEffect(() => {
    const resolveTarget = () => {
      setHeaderTarget(document.querySelector(".modern-dashboard-actions"));
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
