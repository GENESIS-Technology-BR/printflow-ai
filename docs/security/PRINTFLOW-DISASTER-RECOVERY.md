# PRINTFLOW — Disaster Recovery Baseline

Status: PREPARADO / NAO ATIVADO
Versao: 0.1

## Objetivo

Proteger o banco PostgreSQL de producao com uma segunda camada independente do mecanismo nativo do provedor, sem armazenar credenciais ou dumps no repositorio.

## Fonte de verdade

- Aplicacao: PRINTFLOW
- Banco: PostgreSQL
- Database: `neondb`
- Projeto/branch de producao: documentados no inventario operacional da GENESIS
- Credenciais: somente em secret store; nunca neste documento ou no codigo

## Pipeline

Workflow: `.github/workflows/database-backup.yml`
Nome: `PRINTFLOW Database Backup`

O workflow executa `pg_dump` em formato custom, valida o catalogo com `pg_restore --list`, calcula SHA-256 e remove os arquivos do runner ao final.

## Seguranca

1. Usar uma credencial exclusiva para backup, com privilegios minimos de leitura suficientes para `pg_dump`.
2. Armazenar a URL somente no GitHub Actions secret `PRINTFLOW_BACKUP_DATABASE_URL`.
3. Nao reutilizar a URL administrativa da aplicacao como desenho definitivo.
4. Nao registrar URL, usuario, senha ou tokens nos logs.
5. Nao commitar dumps. `.backups/`, `*.db`, `*.sqlite` e `.env` permanecem ignorados.
6. O artifact do GitHub e opcional, manual e com retencao de 1 dia; serve apenas para homologacao controlada, nao como destino definitivo.

## Destino externo

PENDENTE. O backup nao deve ser considerado operacionalmente protegido ate existir uma copia automatica fora do Neon e fora do repositorio GitHub.

Politica alvo inicial:
- 7 backups diarios
- 4 backups semanais
- 3 backups mensais

O destino deve suportar criptografia em repouso, controle de acesso e politica de expiracao.

## Restore

Nunca restaurar um teste diretamente sobre `production`.

Fluxo de homologacao:
1. selecionar um backup validado;
2. criar ambiente/branch isolado de recuperacao;
3. criar banco vazio de homologacao;
4. executar `pg_restore` nesse destino;
5. validar tabelas, contagens e integridade funcional;
6. registrar data, backup utilizado, duracao e resultado;
7. destruir o ambiente temporario somente apos a evidencia ser registrada.

## Criterio de pronto

O controle Backup/Restore somente muda para ATENDIDO quando todos os itens abaixo estiverem comprovados:
- backup automatico diario executando;
- copia independente armazenada;
- checksum validado;
- alerta de falha definido;
- restore isolado concluido com sucesso;
- procedimento e evidencias registrados.

## Estado atual

- Pipeline: PREPARADO
- Secret de backup dedicado: PENDENTE
- Destino externo: PENDENTE
- Backup diario: NAO ATIVADO
- Restore testado: PENDENTE

Nenhuma alteracao de dados de producao e realizada por este baseline.
