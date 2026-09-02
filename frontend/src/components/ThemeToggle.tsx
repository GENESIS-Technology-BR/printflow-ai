import { useEffect, useState } from "react";

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

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const nextTheme = theme === "light" ? "dark" : "light";
  const label = theme === "light" ? "Ativar modo escuro" : "Ativar modo claro";

  return (
    <button
      type="button"
      className="pf-theme-toggle"
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
}
