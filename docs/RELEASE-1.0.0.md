# TALVOA 1.0.0

Baseline oficial de produção.

## Entregue
- Agent Windows com coleta recorrente e heartbeat.
- API autenticada e multiempresa.
- Dashboard, portal do cliente e Control Center.
- Inventário de impressoras com proteção contra snapshot parcial.
- Relatórios Excel/PDF com nomenclatura, IP, número de série, setor e custos.
- Regras comerciais específicas por equipamento.
- Alertas operacionais e monitoramento do Agent.
- Backup privado criptografado com teste de restauração.
- CI com testes backend, segurança, lint, build frontend e smoke test.

## Política de deploy
- Auto-Deploy desabilitado nos serviços principais.
- Alterações são validadas no GitHub Actions.
- Produção recebe somente deploy manual aprovado.

## Baseline
Commit de fechamento: `74adf90489d29b342be27fd16a6698b206635f44`.
