import {
  createOrganizationSector,
  getOrganizationSectors,
  getOrganizationUnits,
} from "./services/api";

function ensureStyles(): void {
  if (document.getElementById("printflow-sector-quick-create-style")) return;
  const style = document.createElement("style");
  style.id = "printflow-sector-quick-create-style";
  style.textContent = `
    .pf-sector-quick-create{display:grid;grid-template-columns:minmax(150px,1fr) auto;gap:6px;align-items:end;min-width:230px}
    .pf-sector-quick-create label{display:grid;gap:4px;font-size:11px;font-weight:600;color:#334155}
    .pf-sector-quick-create input{height:34px;border:1px solid #cbd5e1;border-radius:4px;padding:0 9px;background:#fff;color:#0f172a;font:inherit}
    .pf-sector-quick-create button{height:34px;padding:0 12px;border:0;border-radius:4px;background:#163b5c;color:#fff;font-size:11px;font-weight:700;cursor:pointer;white-space:nowrap}
    .pf-sector-quick-create button:disabled{opacity:.55;cursor:not-allowed}
    .pf-sector-quick-message{grid-column:1/-1;font-size:10px;min-height:12px;color:#166534}
    .pf-sector-quick-message.is-error{color:#b91c1c}
  `;
  document.head.appendChild(style);
}

function enhanceLocationForm(form: HTMLElement): void {
  if (form.dataset.sectorQuickCreate === "1") return;

  const selects = Array.from(form.querySelectorAll("select")) as HTMLSelectElement[];
  if (selects.length < 2) return;

  const unitSelect = selects[0];
  const sectorSelect = selects[1];
  const saveButton = Array.from(form.querySelectorAll("button")).find((button) =>
    button.textContent?.toLowerCase().includes("salvar localização"),
  ) as HTMLButtonElement | undefined;

  if (!saveButton) return;

  form.dataset.sectorQuickCreate = "1";

  const wrapper = document.createElement("div");
  wrapper.className = "pf-sector-quick-create";
  wrapper.innerHTML = `
    <label>Novo setor
      <input type="text" maxlength="120" placeholder="Ex.: PCP" aria-label="Novo setor" />
    </label>
    <button type="button">Cadastrar setor</button>
    <span class="pf-sector-quick-message" aria-live="polite"></span>
  `;

  const input = wrapper.querySelector("input") as HTMLInputElement;
  const button = wrapper.querySelector("button") as HTMLButtonElement;
  const message = wrapper.querySelector(".pf-sector-quick-message") as HTMLSpanElement;

  button.addEventListener("click", async () => {
    const unitName = unitSelect.value.trim();
    const sectorName = input.value.trim();

    message.classList.remove("is-error");
    message.textContent = "";

    if (!unitName) {
      message.textContent = "Selecione uma unidade antes de cadastrar o setor.";
      message.classList.add("is-error");
      return;
    }
    if (sectorName.length < 2) {
      message.textContent = "Informe o nome do setor.";
      message.classList.add("is-error");
      return;
    }

    button.disabled = true;
    button.textContent = "Salvando...";

    try {
      const units = await getOrganizationUnits();
      const unit = units.find((item) => item.name === unitName);
      if (!unit) throw new Error("Unidade selecionada não encontrada no cadastro.");

      const currentSectors = await getOrganizationSectors(unit.id);
      let sector = currentSectors.find(
        (item) => item.name.toLocaleLowerCase("pt-BR") === sectorName.toLocaleLowerCase("pt-BR"),
      );

      if (!sector) {
        sector = await createOrganizationSector(unit.id, sectorName);
      }

      const optionExists = Array.from(sectorSelect.options).some((option) => option.value === sector!.name);
      if (!optionExists) {
        sectorSelect.add(new Option(sector.name, sector.name));
      }

      sectorSelect.value = sector.name;
      sectorSelect.dispatchEvent(new Event("change", { bubbles: true }));
      input.value = "";
      message.textContent = `Setor "${sector.name}" cadastrado e selecionado.`;

      window.setTimeout(() => saveButton.click(), 150);
    } catch (error) {
      message.textContent = error instanceof Error ? error.message : "Falha ao cadastrar o setor.";
      message.classList.add("is-error");
    } finally {
      button.disabled = false;
      button.textContent = "Cadastrar setor";
    }
  });

  form.insertBefore(wrapper, saveButton);
}

function enhancePrinterLocations(): void {
  document.querySelectorAll<HTMLElement>(".printer-clean-location-form").forEach(enhanceLocationForm);
}

ensureStyles();
enhancePrinterLocations();

const observer = new MutationObserver(() => enhancePrinterLocations());
observer.observe(document.documentElement, { childList: true, subtree: true });
