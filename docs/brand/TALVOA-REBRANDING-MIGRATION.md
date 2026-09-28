# TALVOA — Rebranding Oficial e Plano de Migração

## Decisão
A marca oficial do produto passa a ser **TALVOA**.

A partir desta migração, toda comunicação visual, comercial e operacional nova deve utilizar TALVOA.

## O que já passa a ser TALVOA
- Portal web e login
- Portal do cliente
- Control Center
- Dashboard
- Tela de impressoras
- Relatórios Excel e PDF
- Nome dos arquivos de relatório
- E-mails de recuperação
- API/OpenAPI visível
- Workflows GitHub exibidos
- Agent Windows e artefatos de build
- Scripts oficiais de instalação/execução/atualização
- Logger do Agent
- Identidade visual e assets
- Documentação oficial
- Apresentação comercial

## Agent oficial
Nome comercial: **TALVOA Agent**
Executável: `TALVOA-Agent.exe`
Versão do marco de rebranding: **1.1.0**

## Compatibilidade temporária
Os itens abaixo podem manter identificadores antigos internamente durante a transição, pois alterá-los de uma só vez poderia quebrar produção ou instalações já existentes:

- URL pública atual da API Render contendo `printflow`
- URLs técnicas atuais do Render
- Nome atual do repositório GitHub `printflow-ai`
- Secrets GitHub que começam com `PRINTFLOW_`
- Cookies e chaves de sessionStorage existentes
- Variáveis de ambiente antigas `PRINTFLOW_*`
- registros históricos, artefatos e builds anteriores

O código TALVOA deve preferir as novas chaves quando existirem e aceitar aliases antigos durante a janela de migração.

## Novas variáveis suportadas
A aplicação deve priorizar novas variáveis `TALVOA_*` e manter fallback `PRINTFLOW_*` quando necessário para compatibilidade.

## Regra de segurança
Nenhuma credencial, token, secret ou URL de banco deve ser alterada apenas por motivo de branding.

## Próxima fase de infraestrutura
Quando o domínio TALVOA estiver definido:
1. Publicar `talvoa.com.br` ou domínio aprovado.
2. Criar `app.<dominio>`.
3. Criar `api.<dominio>`.
4. Atualizar CORS/TrustedHost.
5. Atualizar Agent para usar o domínio TALVOA.
6. Manter redirect/compatibilidade da URL antiga por período controlado.
7. Só então avaliar renome do repositório e serviços de infraestrutura.

## Critério de homologação do rebranding
- TALVOA Web Validation verde
- TALVOA Production Smoke verde
- Build TALVOA Agent Windows verde
- Portal Render LIVE
- API Render LIVE
- Excel/PDF exibindo TALVOA
- TALVOA Agent instalando e comunicando
- Cliente não visualiza a nomenclatura antiga em nenhuma tela comercial nova
