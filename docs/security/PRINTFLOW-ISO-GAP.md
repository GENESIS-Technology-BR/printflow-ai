# PRINTFLOW — ISO Security GAP Analysis

Status: Em andamento
Versão: 0.1
Escopo inicial: ISO/IEC 27001, ISO/IEC 27002, ISO/IEC 27017 e ISO/IEC 27034

> Este documento é um mapeamento interno de boas práticas e controles de segurança. Não representa certificação ISO nem declaração formal de conformidade.

## Objetivo

Criar o PRINTFLOW Security Framework, identificar controles já existentes, lacunas e prioridades de implementação sem interromper o roadmap funcional do produto.

## Critérios

- ATENDIDO — controle implementado e verificável.
- PARCIAL — existe implementação, mas faltam cobertura, evidência ou hardening.
- GAP — controle relevante ainda não implementado.
- N/A — não aplicável ao escopo atual.

## Baseline inicial

| Área | Referência | Estado inicial | Evidência / situação | Próxima ação |
|---|---|---|---|---|
| Isolamento multiempresa | 27001/27002 | PARCIAL | Tenant scoping existente no backend | ampliar testes negativos e auditoria |
| Autenticação Agent/API | 27001/27002 | PARCIAL | Agent usa token e comunicação autenticada | revisar ciclo de vida, rotação e revogação |
| Segredos locais do Agent | 27001/27002 | PARCIAL | token protegido com DPAPI LocalMachine no Windows | documentar ameaça e recuperação segura |
| Logs e rastreabilidade | 27001/27002 | PARCIAL | logs e telemetria existentes | padronizar eventos de auditoria e retenção |
| Disponibilidade do Agent | 27001/27002 | ATENDIDO/PARCIAL | Scheduled Task, watchdog e auto-recovery | validar operacionalmente no cliente |
| Segurança cloud | 27017 | PARCIAL | API, frontend e PostgreSQL operam em cloud | documentar responsabilidades fornecedor x cliente e hardening |
| SDLC seguro | 27034 | PARCIAL | GitHub Actions, testes, build e smoke antes de produção | adicionar security gates incrementais |
| Dependências | 27034 | PARCIAL | npm audit presente no pipeline | ampliar verificação de dependências Python |
| Gestão de vulnerabilidades | 27001/27002/27034 | GAP | sem processo formal documentado | criar política e severidades |
| Gestão de incidentes | 27001/27002 | GAP | tratamento técnico existe, processo formal não | integrar posteriormente ISO/IEC 27035 |
| Backup e recuperação | 27001/27002/27017 | PARCIAL | updater do Agent possui backup/rollback local | mapear backup de banco/cloud e testes de restauração |
| Criptografia em trânsito | 27001/27002/27017 | PARCIAL | API pública opera sobre HTTPS | documentar e verificar todos os fluxos |
| Controle de acesso administrativo | 27001/27002 | PARCIAL | autenticação existente | revisar RBAC, privilégio mínimo e MFA administrativo |
| Secure coding frontend | 27034 | GAP CRÍTICO | helper legado usa mutação DOM/innerHTML com dados do servidor | migrar painel Agent para React/JSX seguro |
| Privacidade/LGPD | futura 27701/27018 | PENDENTE | fora do baseline inicial | executar segunda fase após security baseline |

## Prioridades técnicas

### P0 — Segurança crítica
1. Remover renderização dinâmica via `innerHTML` no painel operacional do Agent.
2. Revisar autenticação/autorização e testes de isolamento multiempresa.
3. Revisar exposição e ciclo de vida dos tokens do Agent.

### P1 — Hardening
1. Security gates para dependências Python e frontend.
2. Auditoria estruturada de ações administrativas.
3. Política de vulnerabilidades e resposta.
4. Backup/restore documentado e testável.

### P2 — Governança
1. Matriz de responsabilidades cloud PRINTFLOW x cliente.
2. Registro de riscos e aceite de risco.
3. Evidências dos controles implementados.
4. Segunda fase: ISO/IEC 27035, ISO/IEC 27701, ISO/IEC 27018 e LGPD.

## Regra de evolução

Cada alteração de segurança deverá ser pequena, reversível, validada pelo pipeline e associada a uma evidência técnica. O GAP será atualizado progressivamente conforme os controles forem implementados e homologados.
