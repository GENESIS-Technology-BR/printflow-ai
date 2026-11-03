# PR #98 — impedimento preexistente no lint geral

Comando: `pnpm run lint`, em `frontend/`. Resultado: **exit code 1**.

- `src/components/ControlCenter.tsx:126–142`: erro
  `react-hooks/preserve-manual-memoization`. O callback `load`, memoizado com
  dependências `[]`, usa `setError`; o compilador infere essa dependência e não
  consegue preservar a memoização declarada.
- `src/App.tsx:128` e `:139`: dois avisos por diretivas eslint-disable sem efeito.

O problema foi reproduzido na revisão anterior do PR #98 e permanece após a
correção de PartnerPortfolio. Não foi introduzido nem alterado por esta mudança.
O blob de `ControlCenter.tsx` é `d46e8ccedf914338da61045f1d27b6c91ff040ac`,
igual ao de `571888be0b2e0f6ab4aa55e486b04191a4d36cd2` e ao da base do PR.
`App.tsx` também não foi modificado.

O lint específico de `PartnerPortfolio.tsx`, com `--max-warnings=0`, passou sem
erros ou avisos. Não foram desabilitadas regras para ocultar a falha geral.
`ControlCenter.tsx` requer tratamento próprio antes de declarar o lint global
verde; sua alteração não é necessária para corrigir a concorrência do PR #98
e ficou fora deste commit por orientação explícita do usuário.
