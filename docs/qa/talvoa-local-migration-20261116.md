# TALVOA — Plano de migração integral para ambiente local (sem custos adicionais)

**Data:** 16/11/2026 · **Issue:** #103 · **Estado:** planejamento técnico, sem deploy/alterações nos dados.

## 1. Decisão

- **Não adquirir serviços Render.** Preservar instâncias existentes até a homologação local e autorização explícita para exclusão.
- Usar Windows + PostgreSQL 17 como **laboratório de homologação** inicialmente.
- O cluster restaurado `%USERPROFILE%\TALVOA_Restore_Local\pgdata`, porta `127.0.0.1:60439`, contém um **ponto de recuperação histórico**: 7 tabelas / 1303 registros do `Printflow-Production` Supabase. **Não apontar a API nem executar migrações nesse banco original restaurado.** Cluster desligado após validação.
- O banco `talvoa-supritech-homolog-db` no Render está suspenso e **não foi recuperado**. Não tratar o histórico Supabase como equivalente ao banco Render.

## 2. Inventário verificado

| Componente | Estado / origem | Migração local |
| --- | --- | --- |
| Backend | FastAPI, `backend/main.py`, `requirements.txt`; Render web services | Python virtualenv + Uvicorn local, 127.0.0.1:8000 |
| Configuração DB | `backend/app/config/settings.py` lê `DATABASE_URL` e proíbe SQLite em staging/prod | PostgreSQL 17 em base CLONADA independente, URL apenas em variável privada |
| Inicialização | `backend/main.py` executa `Base.metadata.create_all()` e `ensure_*` / outras rotinas para DB que não se chame `talvoa_supritech_homolog_db` | **Bloqueador P0**: não executar contra a base histórica restaurada; revisar/segregar migrações antes da primeira inicialização |
| Schema | Modelos ORM atuais incluem `partners`, `partner_memberships` e colunas mais recentes | Inspecionar diferença frente às 7 tabelas Supabase; preparar migrações em clone apenas |
| Portal | `frontend/package.json`: React 19 + Vite 8, `npm ci` e `npm run build` | Node.js compatível com Vite 8, desenvolvimento localhost:5173 com proxy /api → 127.0.0.1:8000 |
| Agente Windows | Coleta SNMP em rede do cliente, comunica por HTTPS à API | Não redirecionar agentes remotos antes de ter endpoint seguro; validar agente local em LAN primeiro |
| Gateway | Render `talvoa-supritech-homolog-gateway` | Avaliar necessidade real: frontend usa proxy Vite em dev; acesso remoto requer reverse proxy TLS/VPN e autenticação |
| Banco SupriTech Render | Free suspenso após 13/11/2026 | Não migrável automaticamente: só dados independentes e fontes preservadas; avaliar impacto das lacunas |
| Backup recuperável | `Printflow-Supabase-RECUPERADO-1915c6b1253a6452.dump.aesgcm` autenticado, cópia OneDrive Web | Manter cópia local + nuvem, testar restauração periodicamente |

O inventário Render inclui serviços e sites de outras linhas/produtos; **não excluir em lote** ou presumir que todos são TALVOA.

## 3. Gates executáveis, em ordem

### Gate A — Preservação e clone
1. Manter `pgdata` original restaurado **desligado e imutável**; não sobrescrever `.dump` nem `.aesgcm`.
2. Verificar SHA-256 do `.aesgcm` no destino OneDrive independentemente (valor de referência fornecido pelo verificador: `0583D007AF42811E8E0EF98E79ECF9719ABE25F3D4D5E78E077039B8858DDFD5`).
3. Criar **nova base isolada de homologação** a partir do dump de 16/11 em cluster distinto/porta distinta ou por `pg_dump`/restore; manter `127.0.0.1` como único listen_address. Restringir ACL do diretório.
4. Contagem inicial **antes da API** deve igualar: companies_v2=3; users_v2=3; company_units=3; company_sectors=25; printers=35; printer_usage_daily=1080; operational_alerts=154.
5. Senha do cluster e outros segredos exclusivamente no gerenciador de senhas/console protegido, nunca em comandos com valor literal ou GitHub.

### Gate B — Compatibilidade da aplicação (bloqueador)
1. Comparar `information_schema.columns` do clone com `backend/app/database/models.py` e cada modelo ORM, sem copiar dados sensíveis para logs.
2. Examinar `backend/main.py`: no lifespan atual, o caminho não SupriTech invoca `create_all()` e funções de atualização de estrutura/dados. **Não permitir que essa inicialização altere o snapshot recuperado**.
3. Refatorar inicialização para `ENVIRONMENT=local_homologation` com migrações explícitas *separadas* da inicialização ou flag segura `TALVOA_LOCAL_SCHEMA_MIGRATIONS=off` (não implementar sem testes); rodar migrações somente no clone e após diff/revisão.
4. Testar isolamento de empresa, autenticação, modelo parceiro e dados legados após a migração. Nunca tratar `HTTP 200` sozinho como sucesso E2E.

### Gate C — Aplicação e interface local
1. Criar Python virtualenv e instalar `requirements.txt` em diretório de checkout confiável; não usar o Python global como dependência do serviço final.
2. `ENVIRONMENT=homologation`, `DATABASE_URL` apontando para o clone local apenas; `TALVOA_ALLOWED_HOSTS=localhost,127.0.0.1`; `TALVOA_CORS_ORIGINS=http://localhost:5173`; não usar chave secreta de produção.
3. Só iniciar Uvicorn após Gate B; expor somente `127.0.0.1:8000`, nunca `0.0.0.0`.
4. Verificar Node.js compatível com Vite 8; `cd frontend; npm ci; npm run dev -- --host 127.0.0.1`. Proxy `frontend/vite.config.ts` está configurado para API local.
5. Validar login, admin/parceiro/cliente, isolamento multiempresa, inventário e relatórios sem alterar `Printflow-Production`.

### Gate D — Agente e acesso remoto
1. Testar **apenas um agente Windows controlado** contra API local, sem mudar instalação de cliente remoto de produção.
2. Confirmar SNMP/contador físico, fila offline, envio, deduplicação, alertas, separação por tenant e logs.
3. Definir arquitetura de acesso externo: LAN/VPN com TLS e controle de acesso; **um notebook/desktops desligado não substitui um servidor de produção**. Avaliar hardware dedicado, energia, backup, monitoramento e atualizações.
4. Não abrir portas 5432/60439, 8000 ou 5173 diretamente à internet. Agentes remotos não verão localhost do servidor.

### Gate E — Retirada controlada do Render
Somente após evidências de:
- API, portal, agentes, autenticação, relatórios e alertas homologados;
- migrações/contagens conferidas no banco local de operação e backup novo com restore comprovado;
- substituição de cada URL pública de agente/portal, DNS/webhooks/CI/segredos;
- disponibilidade de rede, TLS, energia e plano de suporte local;
- inventário **nominal** dos serviços Render especificamente vinculados à TALVOA, dependências externas removidas, plano de rollback;
- aprovação explícita de exclusão de **cada** serviço e base. Não excluir a base suspensa enquanto houver decisão pendente sobre seus dados.

## 4. Estado em 16/11

**Concluído:** recuperação do histórico Supabase, AES-GCM + OneDrive e restauração em PostgreSQL 17 local com 1303 registros verificados.

**Não concluído:** clone de trabalho, comparação de schema/migrações, API/portal local, agentes remotos, TLS/serviço contínuo e desativação Render.

Nenhum passo deste documento executa alteração automática. Cada gate precisa de evidência e só é marcado após validação real.
