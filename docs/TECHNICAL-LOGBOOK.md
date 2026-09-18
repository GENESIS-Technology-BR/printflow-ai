# PRINTFLOW — Diário de Bordo Técnico

> Registro operacional do projeto. Não registrar senhas, tokens, URLs de banco ou outros secrets neste arquivo.

## 2026-09-18 — Auditoria de produção, segurança e recuperação

### Arquitetura produtiva homologada
- Frontend produtivo: Render `printflow` (`frontend/`).
- API produtiva: Render `printflow-api-genesis`.
- Banco: PostgreSQL Neon, database `neondb`.
- Agent confirmado enviando coleta e heartbeat para `printflow-api-genesis`.
- Fluxo homologado: Agent/Frontend -> API Genesis -> Neon.

### Backup e recuperação
- Backup lógico PostgreSQL diário via GitHub Actions.
- Dump custom validado com `pg_restore --list`.
- Integridade por SHA-256.
- Artifact GitHub com retenção temporária e cópia externa no Google Drive.
- Restore DR separado da produção homologado.
- Último ponto comprovado durante a auditoria: Backup #10.
- Restore Test #3: sucesso em ambiente DR isolado.
- A integração disponível não permitiu confirmar uma execução posterior ao Backup #10; não assumir backup mais novo sem evidência.

### Render
- Serviços oficiais: `printflow` e `printflow-api-genesis`.
- Candidatos legados preservados: `printflow-web` e `printflow-api`.
- Os dois frontends compilam o mesmo código de `frontend/`.
- `printflow-api` permanece com auto-deploy na `main`, porém sem evidência recente de heartbeat/coleta do Agent na janela auditada.
- Nenhum serviço legado foi excluído ou suspenso.
- Antes de desativação: confirmar DNS/custom domains e dependências externas.

### GitHub e CI/CD
- Repositório: `GENESIS-Technology-BR/printflow-ai`.
- Repositório identificado como público durante a auditoria.
- Rulesets retornaram vazios; proteção tradicional da `main` não pôde ser confirmada pela integração.
- Workflows críticos auditados com `permissions: contents: read`.
- Build do Agent executa testes, auditoria de dependências, validação PowerShell, PyInstaller e smoke test do executável.
- Web Validation executa testes backend e build frontend.
- Production Smoke valida a API após workflows bem-sucedidos.
- Risco conhecido: commits na `main` podem disparar auto-deploy Render antes de um gate completo de CI.

### Secrets e histórico
- Nenhum secret real foi identificado na revisão realizada do código atual e dos commits selecionados por palavras-chave.
- Arquivos `.env` não foram encontrados no branch atual e estão cobertos pelo `.gitignore`.
- A revisão histórica foi direcionada por busca e diffs selecionados; não equivale a uma varredura forense de todos os blobs históricos.

### Alterações realizadas
- `render.yaml` alinhado para `printflow-api-genesis` e `/health`.
- Criado `docs/PRODUCTION-ARCHITECTURE.md`.
- Deploys subsequentes foram validados e o Agent continuou retornando HTTP 200 para ingestão/heartbeat.

### Pendências controladas
1. Proteger o caminho `main -> produção` sem bloquear o fluxo de desenvolvimento.
2. Avaliar mudança do repositório proprietário de público para privado após validar acesso do Render.
3. Confirmar DNS/custom domains antes de desativar serviços legados.
4. Melhorar observabilidade de backup/DR: último backup OK, último restore OK e idade do ponto de recuperação.
5. Obter visibilidade administrativa segura do projeto Neon; a conexão Neon disponível na auditoria não listou projetos.


## 2026-09-18 — Homologação Agent v1.0.1 e performance

### Agent Windows
- Build #343 (`v1.0.1`) concluído com sucesso e pacote oficial gerado.
- Upgrade controlado no piloto Guerra Implementos de `v1.0.0` para `v1.0.1`.
- Atualizador preservou token e redes, criou backup pré-upgrade e iniciou o Agent como SYSTEM.
- Portal confirmou Agent `v1.0.1`, estado `healthy`, ciclo automático e 28 impressoras monitoradas.

### Contador de páginas
- HP Laser MFP 432 (`10.2.0.124`) validada contra a interface web física do equipamento.
- Contador físico: 24.321 páginas.
- PRINTFLOW: 24.321 páginas.
- Fluxo HP -> SNMP -> Agent -> API -> banco -> portal homologado para este equipamento.
- A correção monotônica do backend permanece ativa para impedir regressão de contadores confirmados.

### Performance do frontend
- PR #66 integrado à `main`.
- Módulos secundários passaram a carregar sob demanda.
- GETs simultâneos idênticos são deduplicados e respostas recentes usam cache curto de 15 segundos.
- Escritas invalidam o cache.
- Web Validation #43 e Production Smoke #108 concluídos com sucesso.

### Backup/DR — atualização da evidência
- Backup #11, tentativa 2, concluído com sucesso.
- Backup, SHA-256, cópia Google Drive, restore no laboratório DR, validação de tabelas e publicação de evidência concluídos.
- Regra operacional mantida: backup só é considerado OK quando a restauração é comprovada.

## Regra de atualização
Adicionar uma entrada sempre que houver mudança relevante de arquitetura, segurança, deploy, banco, backup/restore, Agent, incidente, homologação ou decisão operacional.
