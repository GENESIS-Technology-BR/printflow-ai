# PRINTFLOW — Trilhos Técnico e Comercial

## 1. Objetivo do produto
PRINTFLOW deve ser apresentado ao mercado como **Gestão Inteligente do Parque de Impressão**, não apenas como monitoramento de impressoras.

Proposta de valor central:
> Controle, visibilidade e previsibilidade sobre todo o parque de impressão em uma única plataforma.

---

## 2. Mapa interno de trabalho

### Trilho Técnico
- Agent Windows e coleta SNMP.
- API e isolamento multiempresa.
- Dashboard operacional.
- Parque de impressão e alertas.
- Relatórios Excel/PDF.
- Segurança, autenticação e auditoria.
- Backup e recuperação.
- Portal do cliente somente leitura.
- Homologação e release v1.0.

### Trilho Comercial
- Posicionamento de marca.
- Apresentação comercial.
- One-page comercial.
- Roteiro de demonstração.
- Planos Essencial / Profissional / Enterprise.
- Ambiente Demo Comercial.
- Processo de onboarding de novos clientes.

---

## 3. Regra de separação de acesso

### Administração PRINTFLOW
Pode:
- cadastrar empresas;
- configurar Agent;
- alterar nomenclaturas;
- alterar setores e organização;
- alterar custos e regras comerciais;
- reconhecer alertas;
- gerenciar usuários;
- acessar Control Center;
- executar manutenção e homologação.

### Cliente
Pode somente consultar:
- Visão Geral;
- Impressoras;
- status, contadores, toner e saúde;
- alertas visíveis;
- relatórios;
- histórico e custos permitidos.

O cliente não deve alterar configurações diretamente. Solicitações de mudança devem ser encaminhadas à equipe PRINTFLOW.

---

## 4. Segurança do portal do cliente
- Sem source maps em produção.
- Segredos, tokens e credenciais nunca devem chegar ao navegador do cliente.
- Autorizações de escrita devem ser validadas no backend.
- Esconder botões não é mecanismo de segurança.
- Cliente opera em perfil somente leitura.
- Dados isolados por empresa.

---

## 5. Experiência proposta para o cliente
Menu principal:
1. Visão Geral
2. Impressoras
3. Relatórios

A administração não aparece para o cliente.

### Visão Geral
- total do parque;
- equipamentos ativos;
- status;
- alertas;
- consumo;
- distribuição por fabricante/setor;
- principais equipamentos por utilização.

### Impressoras
- Nomenclatura;
- IP;
- Nº de série;
- modelo;
- setor;
- páginas;
- toner;
- saúde;
- última comunicação;
- detalhes somente leitura.

### Relatórios
- Excel;
- PDF;
- período;
- setor;
- equipamento;
- custos e fechamento.

---

## 6. Demo Comercial
A Demo Comercial deve ser um ambiente separado da produção.

Regras:
- somente dados fictícios;
- nenhuma informação da Guerra ou de clientes reais;
- empresas, setores e impressoras fictícios;
- indicadores visualmente realistas;
- alertas simulados;
- relatórios de demonstração;
- acesso somente leitura;
- identidade visual equivalente ao produto real.

Objetivo: permitir demonstrações comerciais sem depender de Agent ou rede de cliente.

---

## 7. Apresentação comercial
Estrutura recomendada:
1. O desafio do cliente
2. A solução PRINTFLOW
3. Como funciona
4. Visão Geral
5. Parque e alertas
6. Relatórios
7. Segurança e governança
8. Implantação e planos comerciais

Não apresentar arquitetura interna, banco, builds, credenciais, OIDs, repositório ou detalhes de infraestrutura que não agreguem valor comercial.

---

## 8. Planos comerciais — modelo inicial

### Essencial
- parque monitorado;
- dashboard;
- relatórios padrão;
- alertas básicos.

### Profissional
- dashboard completo;
- relatórios avançados;
- alertas avançados;
- gestão por setor;
- histórico ampliado.

### Enterprise
- multiunidade;
- regras personalizadas;
- integrações;
- relatórios customizados;
- suporte dedicado.

Preços permanecem sob consulta até definição da estratégia comercial.

---

## 9. Critério de evolução
O PRINTFLOW evolui em dois trilhos paralelos:

**Técnico:** estabilidade, segurança, homologação e qualidade.

**Comercial:** demonstração, posicionamento, proposta, planos e aquisição de clientes.

Nenhum recurso comercial deve comprometer isolamento, segurança ou estabilidade da produção.
