# PRINTFLOW — STATUS DE PRODUÇÃO

> Quadro operacional atualizado em 2026-09-24.

## Estado atual

| Item | Status |
|---|---|
| Versão alvo | v1.0 |
| Estado | 🟡 HOMOLOGAÇÃO FINAL |
| API oficial | `printflow-api` — LIVE |
| Banco oficial | Supabase `Printflow-Production` — ACTIVE_HEALTHY |
| Frontend | Render `printflow` — rota atualizada para API oficial |
| Agent | v1.0.1 homologado anteriormente; heartbeat atual precisa nova confirmação |
| DR | backup/restore automatizado existe; restore recente no novo banco ainda precisa ser fechado |
| Serviço legado | `printflow-api-genesis` falha por cota Neon e não deve ser rota padrão |

## Bloqueadores para 100%

1. Confirmar novo heartbeat do Agent contra a API/Supabase oficiais.
2. Executar e comprovar restore DR recente.
3. Validar smoke funcional completo após os deploys.
4. Encerrar dependência operacional do Neon e revisar serviços legados.
5. Atualizar evidências finais de release e marcar v1.0 homologada.

## Regra de produção

`análise → alteração rastreável → deploy → smoke → homologação → fechamento`
