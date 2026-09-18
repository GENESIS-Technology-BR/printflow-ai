# PRINTFLOW — Arquitetura de Produção

## Serviços homologados

- Frontend: Render Static Site, código em `frontend/`.
- API produtiva: Render `printflow-api-genesis`.
- Banco de produção: PostgreSQL Neon (`neondb`).
- Agent: envia coleta para `/api/v1/printers/agent` e heartbeat para `/api/v1/printers/agent/heartbeat`.
- Health check da API: `/health`.

## Fluxo produtivo

```text
PRINTFLOW-Agent -> printflow-api-genesis -> Neon PostgreSQL
Frontend        -> printflow-api-genesis -> Neon PostgreSQL
```

## Proteção e recuperação

- Backup lógico PostgreSQL diário via GitHub Actions.
- Dump em formato custom, validado com `pg_restore --list`.
- Checksum SHA-256.
- Artifact GitHub com retenção de 14 dias.
- Cópia externa no Google Drive.
- Restore testado em banco DR separado da produção.
- O workflow bloqueia restore quando a URL de DR coincide com a credencial de produção.

## Guardrails operacionais

1. Não remover serviços Render legados até confirmar ausência de dependências e tráfego.
2. Não executar restore diretamente na produção.
3. Não registrar URLs de banco, tokens, secrets ou credenciais neste documento.
4. Mudanças em `main` podem disparar auto-deploy no Render.
5. Após deploy da API, validar: status LIVE, `/health`, ingestão do Agent e heartbeat HTTP 200.
6. Antes de mudanças destrutivas, confirmar backup recente e restore DR homologado.

## Serviços legados/candidatos à desativação

- `printflow-api`: não faz parte do caminho padrão atualmente homologado; manter até janela de desativação controlada.
- `printflow-web`: publicação frontend duplicada; manter até confirmação definitiva do endereço utilizado pelos usuários/domínio.

Nenhum serviço legado deve ser excluído apenas com base nesta classificação.
