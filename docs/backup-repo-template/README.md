# TALVOA Backup Repository Template

Destino planejado: `GENESIS-Technology-BR/talvoa-backup`

## Objetivo

Repositório privado e exclusivo para backup e disaster recovery da TALVOA.

## Política de retenção

- Diário: 7 dias
- Semanal: 28 dias
- Mensal: 183 dias
- Evidências de restore: 183 dias

> Em repositório privado, o GitHub permite retenção de artifacts acima de 90 dias, limitada pela política da organização/repositório.

## Segurança

- Nenhum dump é armazenado em claro.
- O dump é validado antes do upload.
- O restore é provado em PostgreSQL efêmero isolado.
- O artifact é criptografado com AES-256-CBC + PBKDF2.
- Produção nunca é usada como destino de restore.
- Secrets permanecem no GitHub Actions Secrets.

## Secrets necessários

- `TALVOA_SUPABASE_DATABASE_PASSWORD`
- `TALVOA_BACKUP_ENCRYPTION_KEY`

## Estrutura esperada no novo repositório

```
.github/
  workflows/
    database-backup.yml
README.md
docs/
  BACKUP-POLICY.md
```

## Ativação

1. Criar o repositório privado `GENESIS-Technology-BR/talvoa-backup`.
2. Garantir que a integração GitHub tenha acesso ao repositório.
3. Copiar o workflow preparado em `docs/backup-repo-template/database-backup.yml`.
4. Criar os dois GitHub Secrets.
5. Em Settings > Actions > General, configurar retenção do repositório para pelo menos 183 dias.
6. Executar manualmente o workflow.
7. Validar geração, restore, criptografia e artifact.
8. Após homologação, desativar o backup no repositório público da aplicação.
