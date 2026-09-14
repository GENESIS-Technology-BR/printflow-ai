// Permite abrir/fechar a edição clicando em qualquer área do resumo da impressora.
// Usa captura no document para funcionar de forma estável mesmo após re-renderizações React.
function isInteractiveTarget(target: HTMLElement): boolean {
  return Boolean(target.closest("button, input, select, textarea, a, label"));
}

function togglePrinterFromTarget(target: HTMLElement): void {
  if (isInteractiveTarget(target)) return;

  const summary = target.closest<HTMLElement>(".printer-clean-summary");
  if (!summary) return;

  const detailsButton = summary.querySelector<HTMLButtonElement>(
    ".printer-clean-details-button",
  );
  if (!detailsButton || detailsButton.disabled) return;

  detailsButton.click();

  // Quando abrir, traz o formulário de edição para a área visível sem mudar a página.
  window.setTimeout(() => {
    const card = summary.closest<HTMLElement>(".printer-clean-card");
    const details = card?.querySelector<HTMLElement>(".printer-clean-details");
    if (details && detailsButton.getAttribute("aria-expanded") === "true") {
      details.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, 60);
}

document.addEventListener(
  "click",
  (event) => {
    const target = event.target as HTMLElement | null;
    if (!target) return;
    togglePrinterFromTarget(target);
  },
  true,
);

document.addEventListener(
  "keydown",
  (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const target = event.target as HTMLElement | null;
    if (!target || isInteractiveTarget(target)) return;

    const summary = target.closest<HTMLElement>(".printer-clean-summary");
    if (!summary) return;

    event.preventDefault();
    togglePrinterFromTarget(target);
  },
  true,
);

const style = document.createElement("style");
style.id = "printflow-printer-row-click-v088";
style.textContent = `
  .printer-clean-summary {
    cursor: pointer !important;
  }
  .printer-clean-summary:hover {
    background: rgba(37, 99, 235, .035);
  }
  .printer-clean-summary .printer-clean-details-button {
    cursor: pointer !important;
  }
`;
if (!document.getElementById(style.id)) {
  document.head.appendChild(style);
}
