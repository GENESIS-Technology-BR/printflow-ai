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

## Evidências automatizadas verificadas em 28/10/2026

- **Build Windows Agent:** GitHub Actions run [40707869265](https://github.com/GENESIS-Technology-BR/printflow-ai/actions/runs/40707869265), sucesso no commit `1592ca44864c62227f8f188f4f8090b3da411e70`; pacote `TALVOA-Agent-Windows-Build-541` publicado. Demonstra apenas compilação, testes e empacotamento em CI, não coleta SNMP no ambiente do cliente (H10).
- **Isolamento HTTP entre parceiros:** GitHub Actions run [40709904456](https://github.com/GENESIS-Technology-BR/printflow-ai/actions/runs/40709904456), sucesso no commit `5a08b24599d977af54fe88e051f8ffd5b31d2c36`; testes HTTP automatizados com banco SQLite de teste. Não substitui validação de cookies, CSRF e sessões no ambiente de homologação (H09), nem auditoria completa H14.
- **Bloqueios remanescentes:** PR #69 não mesclável; homologação live H09–H14 não aprovada; API Render de homologação suspensa por limite gratuito na última verificação. Revalidar disponibilidade antes da demonstração.

Estas evidências **não** alteram os estados da matriz de aceite. Não realizar merge/deploy sem homologação e autorização explícita.

## Auditoria de integração PR #69 — 28/10/2026

- **CI financeiro/Agent:** execução [40726234382](https://github.com/GENESIS-Technology-BR/printflow-ai/actions/runs/40726234382) aprovada no commit `2a8650ae`; execução posterior no commit `a4c9a659` também aprovada, incluindo testes de ano bissexto. Esses resultados não equivalem à homologação SNMP real.
- **CI de isolamento HTTP:** execução [40714205510](https://github.com/GENESIS-Technology-BR/printflow-ai/actions/runs/40714205510) aprovada no commit `116dd946`, incluindo isolamento de diretório de empresas.
- **CI dos robôs somente leitura:** execução aprovada no commit `4a40e357`, após reconciliação do workflow com a versão da branch principal. Os robôs fazem inspeções; não executam deploy.
- **Divergências identificadas ao comparar main com feature:** `.github/workflows/talvoa-robot-readonly.yml`, `backend/modules/usage/router.py`, `backend/tests/test_dashboard_executive_clean.py`. O teste do dashboard já foi alinhado ao texto efetivamente exibido; o workflow foi reconciliado na feature. O cálculo financeiro da feature preserva o ciclo contratual **20–19**, enquanto a main usa mês calendário: **não substituir a implementação da feature pela main** durante a resolução de conflitos.
- **Próximo gate:** reconciliar histórico das branches e resolver conflitos do PR #69 sem descartar a verificação de acesso `require_legacy_company_portal_access`, a cobrança 20–19 nem as rotinas de inspeção somente leitura. Reexecutar CI após a integração e manter H09–H14 pendentes até testes reais.

Nenhum destes resultados autoriza merge, publicação ou mudança de plano gratuito.

## Reconciliação de branches — 28/10/2026

- Commit de integração `657d1d9ed1727eddae358a4352aacb1b1e6c5605`: a feature incorporou o histórico da `main` sem substituir o conteúdo da feature, preservando cobrança por ciclo 20–19 e verificações de acesso do portal legado.
- PR #69: GitHub retornou `mergeable=true` após a reconciliação; isso significa ausência de conflitos de merge, **não** aprovação para publicar.
- No commit de integração, verificações aprovadas: Partner tenancy validation, TALVOA Partner HTTP Isolation, Frontend security audit, TALVOA Virtual Office Checks, TALVOA Demo Preflight, TALVOA Robotic Operations Read-Only e TALVOA Neon Free Usage Monitor. Build Windows Agent estava em execução no momento desta anotação.
- **Gate preservado:** H09–H14 exigem evidência de ambiente real e aprovação explícita antes do merge na `main` ou deploy em produção.
