# Issue #96 — investigação e correção local

Data: 03/11/2026. Branch: `codex/recuperacao-impressoras-96`.
Base local/main/origin/main inspecionada: `7e68c73`. Referência local de
`origin/feature/partner-multitenancy`: `2b36bbf`. Não foi feito fetch; esses
SHAs identificam o histórico disponível neste checkout, não o estado remoto atual.
Issue lida pelo conector GitHub: https://github.com/GENESIS-Technology-BR/printflow-ai/issues/96

## Conclusão e limites

Não existe evidência obtida nesta execução de 27 impressoras reais funcionando
hoje. A melhor evidência histórica encontrada é o registro de homologação em
`235789f` (18/09/2026), `docs/TECHNICAL-LOGBOOK.md`: Agent v1.0.1/build #343,
28 impressoras no portal e contador HP 24.321 comparado ao equipamento físico.
É um relato versionado; logs brutos do cliente e o binário homologado não foram
reexecutados. Não declarar um commit como última versão funcional comprovada
apenas porque compila. `235789f` é a referência documental mais recente encontrada
de homologação física, não uma prova de que todo seu snapshot foi homologado.

Os candidatos `90d0160` e `6a2ea36` adicionam/ativam fallback Printer-MIB;
`a9a86b5` melhora seleção do maior life-count; `4a9657f` corrige a aceitação de
contador confirmado maior sem permitir redução. Todos permanecem no caminho
atual. Reverter para os candidatos descartaria correções posteriores.

## Matriz do fluxo

| Componente | Referência histórica e atual | Evidência / decisão |
|---|---|---|
| Windows / descoberta | `6986237` combina candidatos Windows e redes; atual `core/service.py`, `discovery/safe_windows.py`, launcher TALVOA | `Get-PrinterPort`, validação de candidatos, redes autorizadas e revalidação de IPs conhecidos continuam presentes. Nenhuma regressão impeditiva demonstrada; instalação SYSTEM, interfaces e redes extras exigem cliente real. |
| SNMP | `90d0160`, `6a2ea36`, `a9a86b5`; atual `snmp/page_count_fallback.py` e instalação em `main.py` | WALK da coluna life-count, preservação de fontes específicas e não redução continuam presentes. Testes usam mocks; sem GET/WALK em impressoras reais nesta execução. |
| Envio / fila | exclusão introduzida em `58653d5`; main limita a 500 arquivos/30 dias | Regressão comprovada: `save_to_queue` e `retry_queue` chamam `prune_queue`, que removia pendências antes da confirmação HTTP. 27 leituras por ciclo ultrapassam 500 em 19 ciclos de falha. Correção local preserva pendências e sinaliza excesso no log. |
| API FastAPI / autenticação | `4a9657f`; atual `modules/printers/router.py` | Ingestão autentica token de empresa ativa, procura impressora por empresa+IP, faz merge monotônico e grava histórico. Listagem usa empresa do usuário. Teste sintético cobre 27 equipamentos, repetição de ingestão e isolamento. Não foi iniciado o lifespan da aplicação nem executada migração operacional. |
| Persistência / relatórios | atual modelos Printer/PrinterUsageDaily e módulos usage | SQLite isolado valida persistência, unicidade e histórico; suíte cobre PDF/Excel. Não comprova schema, conteúdo ou disponibilidade de PostgreSQL real. |
| Frontend / destino API | `b71d59b` documenta API oficial em 24/09; `18cb417` alinha Agent; frontend main ainda usava Genesis | Incompatibilidade comprovada nos arquivos: Agent/documentação usam `printflow-api-3uwr`, frontend sem `VITE_API_URL` usava Genesis. Corrigido somente fallback do frontend. Se o build define `VITE_API_URL`, essa variável continua prevalecendo; o destino do build publicado não foi consultado. |
| Inventário / filtros | atual listagem, dashboard e políticas Guerra | Exclusões comerciais de Zebra/DeskJet/IP específico e filtros de ativos podem reduzir totais. Não foram removidos: são políticas explícitas, não evidência de regressão. O total antigo não deve ser forçado com dados fictícios. |

`feature/partner-multitenancy` já contém `574e6f0`, que evita descarte da fila;
a correção não está na main inspecionada. A implementação local mantém os limites
originais como alerta, sem importar a mudança de limites para 100.000 arquivos/365
dias ou todo o conjunto de mudanças de multitenancy. Apenas duas mudanças de
comportamento: preservar fila e alinhar o fallback HTTP do frontend.

O descarte anterior não foi comprovado na máquina do cliente. Esta correção não
recupera arquivos já apagados. Fila preservada pode consumir disco durante falhas
prolongadas: o limite agora gera log de erro, sem apagar medições pendentes.
Reenvio ainda usa a semântica temporal existente do backend; não foi implementado
backfill histórico com data original da coleta.

## Validação reproduzível

Ambiente: Python 3.12.14 em `.venv`; dependências de `requirements-dev.txt`,
mais `httpx` e `tzdata` instaladas localmente. Nenhum manifesto/lockfile foi
atualizado por essa instalação. `tzdata` é necessário para o PDF com
`ZoneInfo('America/Sao_Paulo')` neste Windows. Primeira execução backend:
179 passaram, dois PDFs falharam por ausência dessa dependência; após instalação,
esses testes passaram na suíte completa.

```powershell
$env:DATABASE_URL = 'sqlite://'
$env:ENVIRONMENT = 'test'
$env:PYTHONPATH = "$PWD/agent/python;$PWD"
.venv/Scripts/python.exe -m pytest -q agent/python/tests backend/tests --basetemp=.test-results/tmp-final --junitxml=.test-results/final.xml
.venv/Scripts/python.exe -m pytest -q backend/tests/test_recovery_inventory_96.py backend/tests/test_agent_frontend_api_alignment.py --basetemp=.test-results/tmp-recovery --junitxml=.test-results/recovery.xml
```

- Suíte completa antes da adição do último teste: **282 passaram em 5,03 s**.
- Contratos de alinhamento e recuperação sintética: **2 passaram em 1,08 s**.
  O alinhamento já estava incluído nos 282; são 283 testes distintos aprovados.
- Novo cenário: 27 IPs sintéticos, três ciclos (1000 → 1125 → 900), 27 registros
  finais sem duplicação, contador mantido em 1125, 27 históricos diários,
  outra empresa sem visibilidade e token inválido rejeitado com 401.
- Fila: idade, pressão de quantidade, falha HTTP 503 seguida de confirmação 200,
  preservação do contador e credencial corrente somente na requisição.
- Build: `pnpm run build` (`tsc -b && vite build`) passou, 92 módulos.
  Sem npm no PATH; usado pnpm 11.25.0 e Node 24.22.1 empacotados no runtime.
  Instalação com `pnpm install --lockfile=false`: versões resolvidas pelos ranges
  (Vite 8.3.5, TypeScript 6.0.3, React 19.3.1), não reprodução exata do npm lock.
- `git diff --check` passou.

O sandbox Windows bloqueou diretório temporário padrão e travou o socket local
usado pela criação do event loop asyncio. A execução incompleta foi interrompida;
o comando completo acima passou fora do sandbox, após autorização, com temporários
no workspace. Isso não foi tratado como falha funcional do Agent. Resultados JUnit
locais em `.test-results/final.xml` e `.test-results/recovery.xml`.

## Revisão antes do commit local

Os seis arquivos da missão foram revisados novamente. Nenhuma credencial real,
dependência nova de serviço pago, operação destrutiva ou alteração de produção
foi identificada no diff. Os tokens dos testes são valores sintéticos explícitos.
Não foram encontradas regressões nos cenários cobertos; isso não substitui
homologação física. A pressão de disco da fila preservada permanece como limite
operacional conhecido, descrito acima.

```powershell
$env:DATABASE_URL = 'sqlite://'
$env:ENVIRONMENT = 'test'
$env:PYTHONPATH = "$PWD/agent/python;$PWD"
.venv/Scripts/python.exe -m pytest -q agent/python/tests/test_api_queue_security.py agent/python/tests/test_api_queue_resilience.py agent/python/tests/test_api_sync_resilience.py backend/tests/test_agent_frontend_api_alignment.py backend/tests/test_recovery_inventory_96.py backend/tests/test_printer_usage_history.py backend/tests/test_usage_multitenancy.py --basetemp=.test-results/tmp-review96 --junitxml=.test-results/review96.xml
```

Resultado: **27 passaram em 1,69 s**. Build frontend repetido com sucesso
(`pnpm run build`, 92 módulos). `git diff --check` sem erros. Os resultados
temporários de teste não integram os seis arquivos destinados ao commit.

## Correção P1 do replay — continuação do PR #97

O replay agora processa no máximo um lote por chamada: padrão de **2 arquivos**,
configurável por `TALVOA_QUEUE_BATCH_SIZE` (faixa efetiva 1–20). O limite conta
também arquivos inválidos, evitando ultrapassar o lote ao encontrar dados ruins.
Os arquivos restantes continuam no disco, inclusive acima do limite operacional.

Na primeira falha de conexão/timeout ou resposta diferente de HTTP 200/201,
o lote para. Novas chamadas de replay aguardam **60 segundos** por padrão,
configuráveis por `TALVOA_QUEUE_RETRY_INTERVAL_SECONDS` (mínimo 1 segundo).
O relógio é monotônico; o intervalo fica em memória no cliente do daemon e
reinicia com o processo. Não há sleep bloqueante. Após o intervalo, uma tentativa
bem-sucedida retoma o lote. Resposta sem confirmação não remove o arquivo.

O cooldown vale para replay, não para heartbeat ou envio do inventário corrente.
Este último continua tendo sua política existente de timeout/retries. O inventário
local corrente é salvo antes de qualquer sincronização HTTP e atualizado depois
com o resultado, evitando que a espera do replay deixe a coleta apenas em memória.
O lote limita tentativas, não estabelece deadline absoluto para o ciclo inteiro.

O alerta de pressão da fila (>500 arquivos) continua ativo mesmo durante cooldown,
sem descartar pendências. Os novos logs de falha usam apenas status HTTP e tempo
de espera; não incluem payload, token, corpo de resposta ou texto da exceção.
Arquivos malformados são preservados e falhas de processamento geram aviso.
Rejeição permanente do primeiro item (por exemplo HTTP 422) interrompe o lote e
exige diagnóstico operacional; esta correção não descarta nem quarentena dados.

Testes desta continuação:

- Suíte Agent + backend: **297 passaram em 9,53 s**; JUnit externo ao repositório
  `pr97-p1-full.xml`. Inclui todos os testes presentes no início dessa execução.
- Após adicionar mais um cenário de progresso do inventário corrente, testes
  focados finais: **25 passaram em 1,80 s**, JUnit `pr97-p1-final.xml`.
  São 298 testes distintos aprovados no conjunto das duas execuções.
- Cobertura: 501 pendências/lote configurável, limites de configuração e leitura
  das variáveis pelo serviço, timeout/erro de conexão/HTTP 401, 422, 429 e 503,
  nenhuma nova tentativa durante cooldown, recuperação por HTTP 201, preservação
  dos dados, ausência do token nos logs e persistência corrente antes do HTTP.
- A reprodução anterior de 501 timeouts antes do envio corrente agora tenta
  somente um item, interrompe o replay e segue para o inventário corrente; uma
  chamada subsequente durante cooldown não tenta a fila.
- `git diff --check` sem erros. Nenhuma alteração de frontend, dependência,
  configuração de provedor, credencial ou banco real nesta continuação.

Comandos usados (mesmos DATABASE_URL, ENVIRONMENT e PYTHONPATH acima; basetemp
e JUnit direcionados à pasta externa de evidências):

```text
.venv/Scripts/python.exe -m pytest -q agent/python/tests backend/tests
.venv/Scripts/python.exe -m pytest -q agent/python/tests/test_queue_replay_budget.py agent/python/tests/test_api_queue_security.py agent/python/tests/test_api_queue_resilience.py agent/python/tests/test_api_sync_resilience.py
```

Evidências externas preservadas em
`C:/Users/jandi/.codex/visualizations/2026/11/03/01a1a194-d8a8-7683-9b12-70878c053eb8/`.
A suíte completa foi executada fora do sandbox devido ao bloqueio de socket local
do asyncio no Windows, com dados sintéticos e SQLite em memória. Não houve rede
de impressoras, produção, Render ou Neon. A homologação física segue pendente.
Riscos herdados de colisão de nome por IP/milissegundo, escrita não atômica e
capacidade de disco não foram ampliados de escopo nesta correção do replay.

## Homologação pendente no cliente — não executada

1. Em ambiente de homologação autorizado, conferir que Agent e frontend usam a
   mesma API e empresa. Não expor token; validar login e permissão do usuário.
2. Com uma impressora real autorizada, conferir IP/rede Windows, acesso SNMP,
   fabricante, serial e contador contra a interface física/web do equipamento.
3. Executar ciclo, verificar envio e heartbeat HTTP 200, registro persistido e
   exibição no portal. Repetir ciclo: sem duplicação e sem redução de contador.
4. Imprimir quantidade conhecida e conferir incremento no equipamento, portal e
   histórico. Validar PDF/Excel no período e empresa corretos.
5. Só então confrontar inventário físico completo com os IPs observados. Aceitar
   aproximadamente 27 apenas se essa for a quantidade real elegível; documentar
   impressoras desligadas, redes extras e exclusões comerciais por equipamento.
6. Conferir duas empresas sem vazamento de inventário ou relatórios. Validar fila
   offline/reenvio em homologação e consumo de disco, sem interromper produção.

Nenhuma consulta a bancos reais, alteração de credenciais, ação Render/Neon,
deploy, push ou merge foi executada. Alterações permanecem locais e revisáveis;
PR remoto não foi aberto nesta execução. A issue não pode ser considerada
homologada/encerrada sem os passos físicos acima.
