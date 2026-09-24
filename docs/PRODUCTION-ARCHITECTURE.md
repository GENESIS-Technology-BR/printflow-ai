# PRINTFLOW — Arquitetura de Produção

## Serviços homologados

- Frontend principal: Render `printflow` (`frontend/`).
- API produtiva: Render `printflow-api` — `https://printflow-api-3uwr.onrender.com`.
- Banco de produção: Supabase PostgreSQL — projeto `Printflow-Production`.
- Agent: envia coleta e heartbeat para a API produtiva.
- Serviço `printflow-api-genesis`: legado, ainda configurado com Neon e atualmente bloqueado por cota do provedor. Não usar como rota padrão.

## Fluxo produtivo

```text
PRINTFLOW-Agent -> printflow-api -> Supabase PostgreSQL
Frontend        -> printflow-api -> Supabase PostgreSQL
```

## Proteção e recuperação

- Backup lógico PostgreSQL via GitHub Actions.
- Dump em formato custom, validação por `pg_restore --list` e SHA-256.
- Restore sempre em laboratório DR separado da produção.
- O workflow bloqueia restore quando a URL de DR coincide com a credencial de produção.
- A homologação final do DR requer um restore recente concluído com sucesso no destino DR.

## Guardrails operacionais

1. Não executar restore diretamente na produção.
2. Não registrar URLs de banco com credenciais, tokens ou secrets no repositório.
3. Frontend e Agent devem apontar para `printflow-api`, nunca para o serviço Genesis legado.
4. Após deploy, validar status LIVE, health, ingestão do Agent e heartbeat.
5. Não excluir serviços legados até confirmar ausência de dependências externas.
6. Antes de mudanças destrutivas, confirmar backup recente e restore DR homologado.
