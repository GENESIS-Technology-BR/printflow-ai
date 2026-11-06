# TALVOA — Nova copia recuperavel da SupriTech | 06/11/2026

## Motivo
- O backup anterior esta no OneDrive e passou SHA-256, mas a frase encontrada falhou com InvalidTag. Integridade do arquivo nao equivale a recuperabilidade.
- Render PostgreSQL 16 SupriTech estava available em 06/11; vence em 13/11/2026 17:38 UTC.
- Usar exclusivamente a nova credencial talvoa_supritech_admin_v2; preservar a copia anterior.

## Passos (somente na maquina Windows autorizada)
1. Codex: buscar HEAD de ops/supritech-encrypted-backup-99 sem perder branch local; revisar script ops/talvoa_secure_backup_windows.py, verificar testes offline no Windows e confirmar novo prompt BACKUP recovery passphrase (hidden input).
2. Confirmar Python com cryptography, PostgreSQL 16 pg_dump e pg_restore, acesso permitido no Render e ACL privada. Nao alargar firewall.
3. Executar python ops/talvoa_secure_backup_windows.py em console PowerShell independente e interativo. Jamais colar segredos em argumentos, logs ou chat.
4. Digitar External Database URL da nova credencial em prompt oculto. Criar frase forte nova com pelo menos 20 caracteres, salvando-a IMEDIATAMENTE no gerenciador de senhas, separado do backup.
5. Apos dump e criptografia, digitar novamente a frase armazenada no NOVO prompt de recuperacao. Exigir PASS: independently re-entered passphrase authenticates saved archive. Isso valida a frase contra o arquivo cifrado completo.
6. Copiar apenas o novo .aesgcm para OneDrive/TALVOA-Backups sem sobrescrever; comparar SHA-256 e confirmar presenca e quota no OneDrive Web.
7. Atualizar verificador local para nome/hash do novo arquivo. Restaurar somente em cluster PostgreSQL 16 descartavel isolado em 127.0.0.1; comparar tabelas e linhas; confirmar limpeza do plaintext.
8. Nao encerrar Issue #99 nem excluir copia anterior ate a restauracao comprovada.

## Protecoes
- Sem merge, deploy, alteracao de Render/Neon, firewall ou producao.
- Nao registrar senhas, URL, dumps em plaintext, conteudos reais ou frase de criptografia no GitHub.
- Ferramenta alterada no repo; testes da revisao ainda precisam rodar antes da execucao real.