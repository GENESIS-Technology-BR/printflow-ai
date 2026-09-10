# PRINTFLOW RC1 — Release Gate

Data de preparação: 2026-09-10

Objetivo: congelar um candidato de release validado para piloto controlado.

## Gate automatizado obrigatório

O workflow principal deve concluir com sucesso antes de aprovar a RC1:

- testes automatizados do Agent e Backend;
- auditoria de dependências Python;
- auditoria e build do Frontend;
- validação de sintaxe dos scripts PowerShell;
- compilação dos módulos críticos do Agent;
- geração do executável Windows;
- smoke test do executável;
- validação da integridade do pacote ZIP;
- publicação do artefato do build.

## Gate funcional para piloto

- autenticação e recuperação de senha;
- isolamento multiempresa;
- descoberta e coleta SNMP;
- heartbeat do Agent;
- cadastro de empresa, unidade e setor;
- visualização e personalização de impressoras;
- relatórios consolidados;
- instalação, atualização e watchdog do Agent Windows.

## Critério de aprovação

A RC1 somente é considerada aprovada quando o GitHub Actions da branch `main` estiver verde para este commit e o artefato Windows correspondente estiver disponível.
