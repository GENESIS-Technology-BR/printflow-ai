# TALVOA — Política de sustentabilidade técnica e migração local

**Decisão de 16/11/2026:** adotar **local-first**, sem contratação de serviços, com instalação futura em ambiente controlado do cliente somente após homologação completa. Esta política foi motivada pela expiração do PostgreSQL Free do Render e pela recuperação independente de uma base histórica no Supabase.

## Princípios obrigatórios

1. **Custo zero hoje e previsibilidade amanhã.** Antes de adotar qualquer dependência externa, documentar limites de plano Free (CPU, horas, sono, armazenamento, banco, banda, retenção, execução de jobs, backup, acesso Shell/API), renovação, requisitos de cartão, políticas de suspensão/expiração e mudanças de preço. Uma ferramenta que pode exigir pagamento para recuperar dados é **inadequada como única origem**.
2. **Saída e restauração sem pagar.** Testar exportação de dados e configuração com ferramentas locais, formato aberto (PostgreSQL custom dump + SQL/migrações, JSON quando apropriado) e cópia criptografada independente; *não basta a existência de um botão Backup*. Gate obrigatório: executar restauração local completa e conferir contagens/estrutura.
3. **Portabilidade real.** Código em GitHub não equivale à recuperabilidade. Toda parte essencial deve poder rodar em Windows ou Linux local com instruções reproduzíveis e sem dependência obrigatória de Render/Neon/Supabase/CI. Evitar serviços externos obrigatórios para autenticação e operação; avaliar dependências, licenças e transferência.
4. **Custos transparentes.** Não habilitar upgrades, add-ons, excedentes, compras de créditos nem cartões sem autorização específica. Custo mensal estimado R$0 no laboratório não implica disponibilidade/infraestrutura física gratuita.
5. **Segurança por padrão.** Segredos no gerenciador local, nunca no GitHub/chat. Banco acessível só em 127.0.0.1 durante homologação; rede de cliente, TLS, autorização multiempresa e política LGPD precisam de validação antes de publicar. Não subir dump plaintext.
6. **Uma frente e um critério de aceite por vez.** Diferenciar: código alterado / teste sintético / teste funcional real / homologação no cliente. **Não confundir rótulo de versão com produto entregue.**

## Matriz de decisão para cada ferramenta nova

| Pergunta-gate | Aprovar somente quando… |
| --- | --- |
| Custo | Gratuita para o uso necessário; sem bloqueio ou upgrade obrigatório durante o piloto; limites documentados |
| Dados | Exportação completa no Free e recuperação independente comprovadas |
| Disponibilidade | Suspensão, sono e expiração não impedem operação ou são mitigados por arquitetura local |
| Portabilidade | Alternativa local funcional e procedimento de saída testado |
| Segurança | Segredos, acesso e isolamento de clientes cobertos por testes |
| Manutenção | Dependências atualizáveis sem invalidar backups e migrações |
| Licença | Uso comercial, redistribuição e eventuais limites de fornecedor permitidos |

Se algum gate falhar, **rejeitar a dependência para o caminho crítico** ou registrar exceção temporária com data de saída antes de iniciar implementação.

## Inventário de decisões atuais

| Componente | Decisão | Motivo |
| --- | --- | --- |
| Python 3.11 / FastAPI / Uvicorn | Manter local | Código já existente; precisa preparar venv e validação |
| PostgreSQL 17 | Manter local | Restauração real de 7 tabelas e 1.303 registros do histórico Supabase comprovada |
| React + Vite | Manter | Pode compilar e servir localmente; validar Node suportado |
| GitHub | Manter como repositório de código | Não serve como backup de banco; exportabilidade do código independente |
| Codex Cloud | Apoio opcional para código/testes | Não depender dele para executar operação do cliente |
| Render Free | Retirar depois da homologação | Banco Free suspendeu; sem resgate gratuito comprovado |
| Supabase Free | Manter temporariamente como fonte histórica, nunca única | Exportação e restauração locais comprovadas; verificar dependências de Auth/API e backup |
| Neon | Não tornar obrigatório | Rever qualquer integração existente antes de remoção |
| OneDrive | Cópia externa opcional criptografada | Verificar sincronização web e hash; fornecedor não é fonte operacional única |
| Windows Agent SNMP | Manter como componente no cliente | Testar independente de hospedagem e rota para API segura |

## Caminho de entrega (sem custos de serviço)

### Fase 0 — Preservar (COMPROVADO)
- [x] Dump Supabase `public` de 16/11/2026, 87.598 bytes.
- [x] Cópia AES-256-GCM protegida no OneDrive Web e autenticação comprovada.
- [x] Restauração Postgres 17 local: 7 tabelas e 1.303 registros, cluster desligado corretamente.
- [ ] Comprovar cobertura para Auth e demais schemas/objetos; o backup `--schema public` **não** representa exportação completa de todos os subsistemas Supabase.

### Fase 1 — Laboratório local, SEM tocar na cópia recuperada
- [ ] Criar clone de trabalho em nova base/cluster com ACL privada.
- [ ] Bloquear operações automáticas de `create_all()` e migrações SQL no startup da API até aprovação controlada no clone.
- [ ] Inventariar diferenças entre modelo SQLAlchemy atual e sete tabelas históricas; incluir parceiros/tenants/contadores; preservar evidência.
- [ ] Rodar API e portal somente em localhost; validar autenticação, isolamento, inventário, uso, relatórios.
- [ ] Testar um agente local controlado, contadores reais e recuperação após desconexão.
- [ ] Automatizar backup cifrado local com política de retenção e RESTORE real periódico (sem custos de fornecedor); documentar rota de recuperação.

### Fase 2 — Pacote instalável e portabilidade
- [ ] Criar pacote versionado com API, frontend compilado, migrações idempotentes, serviço Windows/Linux, instalador/rotina de rollback, agent e documentação.
- [ ] Configurar sem segredos predefinidos, arquivo de configuração privado, serviços que iniciam e reiniciam adequadamente, banco local não exposto.
- [ ] Testar **instalação limpa** no segundo computador/VM e **upgrade/rollback** com dados não sensíveis.
- [ ] Validar métricas de uso, disponibilidade, energia, armazenamento e backup no hardware candidato.

### Fase 3 — Instalação no cliente
- [ ] Decidir se o banco/API residirão em servidor local da empresa/cliente ou em servidor central próprio; não presumir multiempresa remota acessível via localhost.
- [ ] Validar segmentação/VLAN, DNS, VPN, TLS, firewall, acesso de suporte e política de dados/LGPD.
- [ ] Piloto com uma empresa/um agente, homologar inventário, contadores, alertas, relatórios e segregação de tenants.
- [ ] Plano de continuidade: energia, backup externo, retenção, restauração, atualização e suporte.
- [ ] Somente após aceite: migrar agentes, DNS/URLs e desligar serviços cloud individuais com rollback; **exclusão requer autorização específica**.

## Critérios objetivos de pronto para cliente

- Instalação limpa repetível e documentada.
- Nenhuma dependência crítica de serviço pago/free volátil.
- Leitura real SNMP com histórico, alertas, relatórios e contas isoladas.
- Backup cifrado e restauração completos testados.
- Serviço seguro e recuperável após reinício/queda.
- Inventário de endpoint remoto e roteamento seguro (VPN/TLS), quando necessário.
- Custos e licenças documentados.
- Checklist de aceite assinado pelo responsável.

**Ação imediata:** focar Gate B da Issue #103: inventário de schema e inicialização segura no clone. Não implantar nem excluir Render antes de cumprir os gates. 
