import { useEffect, useState } from "react";
import type { FormEvent } from "react";

const base = (import.meta.env.VITE_API_URL || "https://printflow-api-genesis.onrender.com").replace(/\/$/, "").replace(/^\/$/, "");
type Partner = { id: number; name: string; active: boolean };
type Member = { id: number; user_id: number; name: string; email: string; role: string; active: boolean };
async function call(path: string, options: RequestInit = {}) {
  const response = await fetch(base + "/api/v1/partners" + path, {
    ...options, credentials: "include",
    headers: { "Content-Type": "application/json", "X-CSRF-Protection": "1", ...options.headers },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Falha na operação");
  return data;
}
export default function PartnerManagement() {
  const [partners, setPartners] = useState<Partner[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  async function refresh() { setPartners(await call("/directory")); }
  async function loadMembers(id: number) { setSelected(id); setMembers(await call(`/directory/${id}/members`)); }
  useEffect(() => { refresh().catch(e => setError(String(e))); }, []);
  async function execute(work: () => Promise<void>) {
    setBusy(true); setError(""); setNotice("");
    try { await work(); setNotice("Alteração salva com sucesso."); }
    catch (e) { setError(e instanceof Error ? e.message : "Erro na operação"); }
    finally { setBusy(false); }
  }
  async function addPartner(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); const form = e.currentTarget;
    await execute(async () => {
      const fd = new FormData(form);
      await call("/directory", { method: "POST", body: JSON.stringify({ name: fd.get("name") }) });
      await refresh(); form.reset();
    });
  }
  async function addUser(e: FormEvent<HTMLFormElement>) {
    e.preventDefault(); if (selected === null) return;
    const form = e.currentTarget;
    await execute(async () => {
      const fd = new FormData(form);
      await call(`/directory/${selected}/users`, {
        method: "POST", body: JSON.stringify({
          name: fd.get("name"), email: fd.get("email"), username: fd.get("username"),
          password: fd.get("password"), role: fd.get("role"),
        }),
      });
      await loadMembers(selected); form.reset();
    });
  }
  async function assignUsername(e: FormEvent<HTMLFormElement>, memberId: number) {
    e.preventDefault(); if (selected === null) return;
    const fd = new FormData(e.currentTarget);
    await execute(async () => {
      await call(`/directory/${selected}/members/${memberId}/username`, {
        method: "PATCH", body: JSON.stringify({ username: fd.get("username") }),
      });
      await loadMembers(selected);
    });
  }
  return <section style={{ padding: 24, maxWidth: 1050 }}>
    <h1>Gestão de Parceiros</h1>
    <p>Cadastro e administração de revendas TALVOA. Acesso exclusivo ao administrador da plataforma.</p>
    {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
    {notice && <p role="status">{notice}</p>}
    <h2>Parceiros cadastrados</h2>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
      {partners.map(p => <button key={p.id} type="button" disabled={busy}
        onClick={() => loadMembers(p.id).catch(e => setError(String(e)))}>
        {p.name} {p.active ? "" : "(inativo)"} {selected === p.id ? "✓" : ""}
      </button>)}
    </div>
    <form onSubmit={addPartner} style={{ marginTop: 16 }}>
      <label>Novo parceiro <input name="name" minLength={2} maxLength={180} required /></label>
      <button disabled={busy}>Cadastrar parceiro</button>
    </form>
    {selected !== null && <>
      <h2>Usuários do parceiro</h2>
      {members.map(m => <div key={m.id} style={{ padding: 12, marginBottom: 8, border: "1px solid #ccc", borderRadius: 6 }}>
        <strong>{m.name}</strong> — {m.email} — {m.role} — {m.active ? "Ativo" : "Inativo"}
        <form onSubmit={e => assignUsername(e, m.id)} style={{ display: "flex", gap: 8, marginTop: 8 }}>
          <label>Definir usuário <input name="username" placeholder="supritech" required minLength={3} maxLength={60} pattern="[a-zA-Z][a-zA-Z0-9._-]{2,59}" /></label>
          <button disabled={busy}>Salvar usuário</button>
        </form>
      </div>)}
      <h3>Cadastrar novo usuário</h3>
      <form onSubmit={addUser} style={{ display: "grid", gap: 12, maxWidth: 520 }}>
        <label>Nome <input name="name" required minLength={3} /></label>
        <label>Usuário <input name="username" required minLength={3} pattern="[a-zA-Z][a-zA-Z0-9._-]{2,59}" /></label>
        <label>E-mail <input name="email" type="email" required /></label>
        <label>Senha inicial <input name="password" type="password" required minLength={12} autoComplete="new-password" /></label>
        <label>Perfil <select name="role"><option value="partner_admin">Administrador</option><option value="partner_operator">Operador</option><option value="partner_viewer">Consulta</option></select></label>
        <button disabled={busy}>Criar usuário do parceiro</button>
      </form>
    </>}
  </section>;
}
