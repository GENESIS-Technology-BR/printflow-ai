// Torna toda a linha-resumo da impressora acionável para abrir/fechar a edição.
// O listener é delegado para continuar funcionando após filtros e re-renderizações React.
document.addEventListener("click", (event) => {
  const target = event.target as HTMLElement | null;
  if (!target) return;

  const summary = target.closest<HTMLElement>(".printer-clean-summary");
  if (!summary) return;

  // Controles explícitos continuam com seu comportamento próprio.
  if (target.closest("button, input, select, textarea, a, label")) return;

  const detailsButton = summary.querySelector<HTMLButtonElement>(
    ".printer-clean-details-button",
  );
  detailsButton?.click();
});

// Feedback visual de que a linha inteira pode ser aberta.
const style = document.createElement("style");
style.textContent = `
  .printer-clean-summary { cursor: pointer; }
  .printer-clean-summary .printer-clean-details-button { cursor: pointer; }
`;
document.head.appendChild(style);
