# TALVOA 1.0 — Homologação de parceiros e multiempresa

Status: em andamento. Este documento não constitui aceite para produção.

## Matriz de aceite

| ID | Cenário | Evidência exigida | Estado |
|---|---|---|---|
| H01 | TALVOA cadastra parceiro | 201; somente platform_admin; duplicidade 409 | Teste unitário automatizado |
| H02 | TALVOA vincula usuário ao parceiro | Papel válido, usuário ativo, somente platform_admin; duplicidade 409 | Teste unitário automatizado |
| H03 | TALVOA vincula empresa ainda sem parceiro | Sem transferência entre parceiros; portal desabilitado | Teste unitário automatizado |
| H04 | Parceiro tenta ler outra empresa | 403 para inventário, alertas e visão geral | Teste unitário automatizado (parcial) |
| H05 | Cliente final acessa portal | Somente com opt-in para empresa vinculada | Teste unitário automatizado |
| H06 | Empresa legada sem parceiro | Acesso legado preservado | Teste unitário automatizado |
| H07 | Indicadores de impressoras | Resumo da carteira igual à soma das empresas, com exclusões comerciais | Teste unitário automatizado |
| H08 | Inventário de impressoras | Somente campos operacionais permitidos; sem credenciais | Teste unitário automatizado |
| H09 | Fluxo HTTP real com cookies e CSRF | Login, 401/403/409, sessão expirada, alteração de portal | Pendente |
| H10 | Agent de produção e coleta SNMP | Coleta e contadores sem regressão | Pendente |
| H11 | Relatórios PDF/Excel e faturamento | Conferência de valores, exclusões, período de corte | Pendente |
| H12 | Backup e restauração | Restauração isolada e integridade de dados | Pendente |
| H13 | Deploy/rollback | Migração reversível ou plano de reversão verificado | Pendente |
| H14 | Pentest básico | Autorização por objeto, sessão, rate limit, vazamento de segredo | Pendente |

## Regras de segurança

- Não executar H10–H14 sobre produção sem plano de teste e autorização apropriada.
- Nunca transferir empresas já vinculadas entre parceiros por endpoint de onboarding.
- Nunca habilitar portal do cliente automaticamente durante a associação.
- Não fazer merge da PR ou deploy da branch antes do aceite dos cenários críticos.
- Registrar SHA do commit, GitHub Actions, evidências de ambiente e responsável por cada aceite.

## Gate de publicação

Zero falhas críticas; isolamento comprovado em HTTP; relatório e Agent validados; backup/restauração e rollback demonstrados; aprovação explícita de publicação.
