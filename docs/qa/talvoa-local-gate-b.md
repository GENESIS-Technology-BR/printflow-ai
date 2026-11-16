# TALVOA — Gate B: inicialização local sem modificar backup histórico

**Estado:** código e regressões publicados na branch de homologação; **não validado em Windows nem em um clone real**.

## Regra de isolamento

- O PostgreSQL 17 original recuperado é somente evidência histórica: `127.0.0.1:60439/talvoa_recuperacao_20261116`, 7 tabelas / 1.303 linhas. **Nunca iniciar a API apontando para essa URL.**
- Usar exclusivamente clone descartável **`127.0.0.1:60440/talvoa_local_work_*`** em cluster separado. As senhas não devem constar em arquivo versionado, comando de terminal visível ou GitHub.
- `ENVIRONMENT=local_homologation` exige `DATABASE_URL` PostgreSQL apontando ao loopback, porta 60440, usuário e senha, banco com prefixo `talvoa_local_work_`. Sem configurações válidas, o processo recusa inicialização.
- Nesse modo, `backend/main.py` **não executa** `Base.metadata.create_all()`, `ensure_*`, `clean_descriptive_printer_serials()` nem `configure_guerra_pilot_financials()` durante o startup. O bootstrap automático de administrador também fica desativado.
- Essa proteção não torna a aplicação inteira de somente leitura: **rotas HTTP podem gravar dados no clone de trabalho**. Por isso, não direcionar agentes/clientes existentes ao servidor de testes antes de autorizar e isolar.
- O caminho legado de outros ambientes não foi modificado (ainda requer auditoria antes de novas implantações).

## Validação mínima antes de executar

1. Na branch `ops/talvoa-local-migration-103`, rodar: `python -m unittest tests.test_local_homologation_guard -v` em checkout isolado, sem secrets.
2. Verificar que modo local com URL de produção, Supabase, Render, porta 60439 ou `talvoa_recuperacao_20261116` **falha antes de criar engine**.
3. Criar clone separado a partir do `.dump` local de 16/11 em cluster PostgreSQL 17 privado, porta 60440; nunca copiar `pgdata` diretamente com PostgreSQL em funcionamento.
4. Restaurar no clone, comparar 7 tabelas e 1.303 linhas **antes de API**. A ferramenta de restauração é externa à API e deve ser testada/operada de forma supervisionada.
5. Inspecionar diferenças entre ORM da branch atual e histórico antes de migrações explícitas no clone. A branch da API exige tabelas de parceiros ainda não presentes no histórico; **não usar `create_all` automaticamente**.
6. Instalar ambiente virtual Python para API e Node compatível com Vite 8 para frontend. Não iniciar agente real nesta fase.
7. Testar carregamento da API na porta 8000 e portal 5173 só em loopback; comportamento de logins/relatórios condicionado a migrações necessárias no clone.
8. Anotar resultado em Issue #103: versão/commit, testes, snapshots de contagens agregadas, divergências e próximo gate; não anexar dados pessoais ou credenciais.

## Limites

A restauração histórica é de `public` do Supabase; não inclui automaticamente os componentes `auth`, `storage` e todas as configurações. Validação de autenticação da TALVOA deve ser específica e não supor que usuários e senhas do Supabase foram restaurados.

**NÃO há autorização para:** alterar Supabase, Render, banco histórico, produção, DNS ou redes; excluir serviços; comprar créditos; migrar agentes/clientes.
