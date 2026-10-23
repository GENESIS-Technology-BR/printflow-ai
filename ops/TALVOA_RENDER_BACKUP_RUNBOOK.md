# TALVOA — Backup operacional Render PostgreSQL (SupriTech)

**Banco origem:** `dpg-db7rsb25b2lc739g0img-a` (PostgreSQL 16, Render Free).
**Vencimento:** 2026-11-13 17:38:52 UTC.
**Destino planejado:** Neon `red-hat-77865204` (PostgreSQL 18), **ainda vazio**.

## Diagnóstico 2026-10-23
- Banco Render está disponível; não há backup ou restore verificado.
- Consulta read-only pelo conector Render falhou: conexão externa não passou pela exigência TLS / lista de IPs; conector hospedado não tem IP fixo para liberar.
- Existe regra externa temporária `201.72.238.194/32`; não ampliar para `0.0.0.0/0`.
- Script `ops/backup_supritech_homolog.sh` está na branch `chore/supritech-readonly-account-audit`, mas **não foi executado**.
- Neon PG18 exige teste de restauração a partir de PG16 antes de migração. Não alterar DATABASE_URL de serviços.

## Procedimento seguro (operador autorizado)
1. Escolher host sob controle do operador com cliente `pg_dump` compatível com PostgreSQL 16 e acesso de rede ao Render. Usar TLS.
2. Guardar `DATABASE_URL` apenas em variável de ambiente protegida, sem colar no chat, GitHub ou logs.
3. Executar `ops/backup_supritech_homolog.sh` com `BACKUP_DIR` privado, fora do repositório.
4. Conferir SHA-256 e catálogo do arquivo. **Isso não comprova recuperação.**
5. Fazer restore em PostgreSQL isolado e descartável; validar esquema, dados e permissões.
6. Criptografar o dump em repouso e manter cópia independente, com acesso restrito.
7. Somente após restore validado, planejar migração para Neon; nunca executar cutover sem aprovação.

## Critérios de aceite
- Arquivo dump criado e checksum conferido.
- Restore completo concluído sem erros.
- Comparação de tabelas/linhas e smoke tests documentados.
- Cópia protegida em armazenamento independente.
- Registro de operador, data, resultado e destino protegido (sem credenciais).

## Situação
**BLOQUEADO PARA MIGRAÇÃO** até existir backup restaurado e testado.
