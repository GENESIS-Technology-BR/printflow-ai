# TALVOA — Política de Backup e Disaster Recovery

## Escopo

Banco PostgreSQL de produção da TALVOA hospedado no Supabase.

## Frequência

- Backup lógico diário às 02:00 America/Sao_Paulo.
- O mesmo dump diário é classificado para retenção semanal e mensal quando aplicável.

## Retenção

- Diário: 7 dias.
- Semanal: 28 dias.
- Mensal: 183 dias.
- Evidência de restore: 183 dias.

## Controles de integridade

Cada execução:
1. gera `pg_dump` em formato custom;
2. valida o catálogo com `pg_restore --list`;
3. gera SHA-256;
4. restaura em PostgreSQL 18 efêmero;
5. valida tabelas essenciais e dados de aplicação;
6. criptografa o dump;
7. publica somente o arquivo criptografado como artifact.

## Segurança

- Restore nunca aponta para produção.
- Dumps não são armazenados no Git.
- Dumps não são publicados sem criptografia.
- Chaves e senhas ficam somente em GitHub Actions Secrets.
- O repositório de backup deve permanecer privado.
- A aplicação TALVOA não depende deste repositório para funcionar.

## Teste periódico

Executar restore manual de homologação pelo menos uma vez por mês, além do restore automático de cada execução.

## Responsabilidade

Este repositório é exclusivamente para continuidade, backup e recuperação.
