# TALVOA Render — auditoria 2026-10-30

- Limite Free excedido: 757,02/750 horas; banda 1,31/5 GB; pipeline 63/500 min.
- Render suspendeu APIs em 26/10/2026: Free Tier Usage Exceeded.
- Deploys anteriores bem-sucedidos não significam serviços operacionais.
- API SupriTech e gateway: autoDeploy off; preservar produção.
- PostgreSQL SupriTech homolog: disponível, Free, expira 2026-11-13T17:38:52Z.
- Backup não verificado. Usar ops/backup_supritech_homolog.sh apenas em host autorizado; testar restore isolado antes de migração.
- Não alterar allowlist, credenciais, plano, DATABASE_URL, bancos ou serviços de produção sem validação.
- Auditar UptimeRobot e cron externos: causa atribuível a pings ainda NÃO comprovada.
- Após renovação de franquia, manter uma única API Free de cada vez quando possível; desativar probes que acordam APIs sem necessidade, preservando alertas relevantes.
- Sem garantia de 24/7 em plano Free; acompanhar consumo diário.
- Nenhuma alteração em monitor externo nem dump de dados realizada nesta auditoria.
