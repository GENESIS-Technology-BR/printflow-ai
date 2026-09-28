# TALVOA v1.0 — Homologação Guerra

## Build oficial do Agent
- Build: 355
- Artefato: TALVOA-Agent-Windows-Build-355
- Status GitHub Actions: SUCCESS
- Commit do Agent: aaff4c55a27f19fed7589e26ed638e565144632d

## Backend / Produção
- API Render: LIVE
- Web Validation 169: SUCCESS
- Production Smoke 247: SUCCESS
- Recuperação temporária de admin: removida
- Variáveis temporárias de recovery: neutralizadas

## Regras comerciais Guerra
- P&B: R$ 0,05/página
- Colorida: R$ 0,35/página
- Canon iPF-770 IP 10.2.0.109: R$ 1.500/mês (valor fixo)
- Impressoras Zebra: fora da visão comercial e relatórios
- HP DeskJet 2700 IP 10.2.128.31: fora do outsourcing, dashboard e relatórios

## Testes de homologação no cliente
1. Instalar/executar a Build 355.
2. Confirmar Agent Online no dashboard.
3. Confirmar atualização de last_seen.
4. Validar coleta do IP 10.2.127.18.
5. Confirmar ausência da DeskJet 10.2.128.31.
6. Confirmar ausência das Zebra na visão comercial.
7. Validar contadores de pelo menos 3 impressoras físicas.
8. Gerar Excel do período atual.
9. Gerar PDF do período atual.
10. Conferir custos P&B, cor e Canon fixa.
11. Validar alertas amarelo/vermelho.
12. Registrar evidência final da homologação.

## Pendência isolada
- Backup automático GitHub Actions aguardando atualização do secret da senha atual do Supabase.

## Critério para fechar v1.0
A release pode ser considerada homologada quando os itens 2 a 11 acima estiverem validados no ambiente da Guerra e o backup automático estiver novamente verde.
