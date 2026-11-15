# Missão #99 — ensaio Linux no Codex Cloud

## Escopo e reprodução

`ops/talvoa_m99_cloud_synthetic.py` é uma rotina executável de backup e restauração
**exclusivamente sintética**. Não aceita URL, senha, arquivo de cliente ou destino
remoto. Usa as funções AES-256-GCM/scrypt já versionadas, compatíveis com Linux.
Não comprova recuperabilidade do backup real; #99 deve permanecer aberta.

Pré-requisitos: Linux, Python 3.12, Docker local disponível ao usuário e espaço
para a imagem oficial PostgreSQL. Execute no checkout da branch
`ops/supritech-encrypted-backup-99`:

```sh
python -m venv /workspace/work/m99-venv
/workspace/work/m99-venv/bin/python -m pip install 'cryptography>=42,<48'
env -u DOCKER_HOST -u DOCKER_CONTEXT -u DOCKER_TLS -u DOCKER_TLS_VERIFY -u DOCKER_CERT_PATH \
  docker --host=unix:///var/run/docker.sock pull \
  postgres:16-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9
/workspace/work/m99-venv/bin/python ops/talvoa_m99_cloud_synthetic.py --synthetic-only
```

Instalação/download precedem o ensaio. O processo PostgreSQL roda sem rede:
`--network=none`, sem publicação de portas, `listen_addresses=''`, somente
socket Unix `/tmp`, UID/GID 999, filesystem raiz somente leitura, capabilities
removidas, limites de CPU/memória/processos. Cluster novo com checksums em tmpfs;
nenhum bind mount, volume durável ou conexão remota. Autenticação local trust
serve somente ao socket deste contêiner descartável, sem dados reais; autenticação
host é reject. Não reutilizar essa configuração para banco de cliente.

A rotina cria duas tabelas (3 e 5 linhas), PK/FK/check/unique, índice, view e
sequências. Gera `pg_dump -Fc`, cifra com chave aleatória efêmera não registrada,
rejeita chave errada e adulteração sem deixar plaintext, autentica e decifra a
cópia válida, verifica igualdade byte a byte e `pg_restore --list`, restaura em
outro database novo com transação única e parada no primeiro erro. Compara
conteúdo agregado, schema/constraints/índices/view e testa sequência e FK restauradas.
O JSON final contém somente evidência sintética. Arquivos temporários ficam em
diretório privado 0700, removido ao final; contêiner removido em `finally`, inclusive
em falha de inicialização e SIGTERM/KeyboardInterrupt. SIGKILL/queda do runtime
não permitem executar `finally`: verificar contêineres com label
`talvoa.m99=synthetic` antes de encerrar a sessão, sem remover recursos alheios.

## Investigação de conectividade — sem tocar o banco

Em 07/11/2026 (America/Sao_Paulo), a sessão Cloud declara política HTTP
`unrestricted/enforced`, mas o snapshot `/etc/codex/network-policy.json`
declara `tcp_network_access.domains=[]`, `ip_ranges=[]`, VPN não configurada;
status atual não declara secrets nem identidades de saída. HTTP liberado
**não estabelece permissão/rota TCP PostgreSQL**. Não foram feitos DNS/probe TCP,
SSLRequest, login, SQL ou dump no endpoint real, nem consultadas credenciais.
Não se afirma que houve rejeição de conexão: conectividade real não foi testada.

Conforme histórico de #99, a allowlist Render está restrita ao IP da estação
autorizada. Não foi revalidada nem alterada nesta execução. Não existe evidência
de egress fixo/autorizado do Codex Cloud que coincida com esse IP. Portanto,
**acesso seguro direto não demonstrado com a configuração atual**; parar antes
de qualquer tentativa real. HTTPS proxy não substitui túnel PostgreSQL.

Documentação oficial lida nesta execução:

- https://render.com/docs/postgresql-creating-connecting — externo exige TLS,
  hostname completo e allowlist; interno exige mesma conta e região.
- https://render.com/docs/ssh — web Free não oferece Shell nem SSH.
- https://render.com/docs/free — web Free pode enviar tráfego privado, mas não
  oferece Shell/SSH nem one-off jobs; limites incluídos de horas/banda/build existem.

O MCP Render não tem workspace selecionado nesta sessão; não selecionamos
workspace por inferência nem acessamos recursos. Assim, não foi confirmada a
existência de serviço elegível, ferramenta PG16 ou quota disponível.

## Alternativa online de menor risco e custo incremental zero

1. **Se já existir serviço Render com Shell incluído no plano contratado**, na
   mesma conta/região do banco, preferir operação única via Shell autenticado do
   Dashboard, sem deploy, sem novo serviço e sem alterar allowlist. Validar antes
   PG16, memória/CPU disponíveis e quota de transferência; não garantir custo zero
   se isso exigir upgrade ou exceder quota. Não usar banco de produção como destino
   de restauração e não sobrecarregar serviço ativo.
2. Somente em futura execução especificamente autorizada: credencial existente
   disponibilizada pelo mecanismo de secrets, sem chat/argumentos/logs; conexão
   interna com TLS obrigatório; dump custom, criptografia antes da transferência,
   chave guardada separadamente pelo responsável; arquivo cifrado em armazenamento
   independente já contratado e com quota disponível. Nenhum dump em GitHub ou
   artifact público. Restore descartável no Cloud, sem rede, exige ambiente e
   tratamento de secrets adequados a dados reais; esta rotina sintética não aceita
   esse arquivo nem deve ser usada como ferramenta de restore de cliente.
3. **Se todos os serviços forem Free, não há caminho 100% cloud, sem deploy,
   sem mudança de rede e com custo zero comprovado nesta sessão.** Não criar
   endpoint de backup público, túnel ou serviço pago para contornar isso. A opção
   zero adicional comprovadamente compatível com a allowlist histórica é a estação
   já autorizada executando backup online via TLS, com armazenamento cifrado já
   contratado. Essa alternativa usa a estação e não satisfaz o requisito 100% cloud.
   Runner GitHub hospedado tem saída diferente e não resolve a allowlist; runner
   próprio na estação continua dependendo dela.

Nenhuma dessas operações reais foi executada. Não houve merge, deploy, mudança
de billing/rede ou compra de créditos. A validação feita usa recursos da sessão
Cloud existente; não foi disparado workflow GitHub Actions.

## Evidência da execução

- Data: 07/11/2026 23:02 America/Sao_Paulo
  (2026-11-08T02:02:03Z); base `9b7a82cef01a23867d5b6b33962b4e257d5bd9ab`.
- Linux, Python 3.12.14, cryptography 47.0.0, PostgreSQL/pg_dump 16.15.
- 30 testes offline aprovados (0,824 s), incluindo dois novos casos de limpeza
  em falha de partida/readiness. Conexões Python bloqueadas por mocks no runner.
- Ensaio end-to-end final: PASS; 2 tabelas, 8 linhas; conteúdo/inventário iguais,
  sequência e FK verificadas; chave errada/adulteração rejeitadas sem plaintext residual.
- Dump **sintético**: 5.784 bytes; SHA-256
  `c6ddcd4ac8148dc81743c33737e60f3a9739b51be02ebfa74c1aac050ff05749`.
- Arquivo cifrado **sintético**: 5.836 bytes; SHA-256
  `62af2fc541cb536885c76a29357bb2b7fdbecd7a99a9aa9867f6ac3c43fc6741`.
- `network=none`, sem listener TCP; temporários e contêiner removidos.
  Consulta posterior de contêineres com label da missão retornou lista vazia.
- Sintaxe Python aprovada; nenhuma senha pedida ou divulgada. Hashes variam em
  novas execuções por metadados do dump e salt/nonce aleatórios da criptografia.
