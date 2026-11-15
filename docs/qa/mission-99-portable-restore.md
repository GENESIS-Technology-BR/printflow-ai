# TALVOA — Missão #99: recuperação portátil (05/11/2026)

## Situação atual (não confundir com restore concluído)
- O backup real foi gerado em 04/11/2026 com `pg_dump` PostgreSQL 16, criptografado AES-256-GCM.
- Arquivo confirmado visualmente no OneDrive Web, pasta `TALVOA-Backups`:
  `supritech-20261104T175511Z-656276385a8791e2.dump.aesgcm`.
- SHA-256 validado anteriormente contra cópias local/OneDrive: `55f4ea0533895c1ae4e7f827b02e58b93145b8fd86d319ea53a98de45628de4a`, 55.687 bytes.
- O usuário está em **outro perfil/máquina** do usado no backup (`C:\Users\Jandir Junior` versus `C:\Users\jandi`). O cluster temporário `127.0.0.1:60439` não está em execução nesse novo perfil. O script temporário `restore_mission99_manual.py` não é repositório versionado e não foi localizado; **não insistir naquele caminho**.
- **Restauração real ainda não ocorreu.** Nenhuma afirmação de tabelas recuperadas até executá-la.

## Fluxo sem copiar comandos de um chat a outro
1. Codex Windows consulta diretamente [Issue #99](https://github.com/GENESIS-Technology-BR/printflow-ai/issues/99) e [PR #100](https://github.com/GENESIS-Technology-BR/printflow-ai/pull/100), faz fetch da branch `ops/supritech-encrypted-backup-99` para um checkout separado, preservando alterações locais.
2. Usuário abre [OneDrive — Meus arquivos](https://onedrive.live.com/my), pasta `TALVOA-Backups`, e usa **Baixar** para disponibilizar o arquivo na máquina atual. **Não** compartilhar link público nem senhas; jamais subir dump para GitHub.
3. Executar o preflight offline, sem rede ou senha (Python 3.10+):
   `python ops/talvoa_restore_m99_preflight.py --backup "CAMINHO_LOCAL_DO_ARQUIVO.aesgcm"`
   Ou sem `--backup` se o OneDrive está sincronizado no perfil. O script encontra o arquivo de forma independente do nome do usuário e confere tamanho e SHA-256 fixos; se divergir, parar.
4. Codex deve localizar PostgreSQL 16 instalado (ou instalar clientes/servidor 16 somente com aprovação do usuário) e **preparar cluster novo, isolado local, com SCRAM, pasta privada e porta livre**. `127.0.0.1:60439` só pode ser reutilizada se for um cluster novo comprovadamente isolado. Rejeitar conexões remotas, exigir `listen_addresses=127.0.0.1` e verificar processo proprietário da porta.
5. Antes de escrever qualquer dump em plaintext: verificar ACL privada real no Windows, executar `ops/talvoa_decrypt_backup_windows.py` com `--output` em pasta privada, usando **a frase secreta em entrada oculta no console do usuário**. Essa ferramenta valida AES-GCM e `pg_restore --list`; não realiza conexão com banco.
6. Restaurar **apenas** no banco descartável local e criado explicitamente para #99, preferencialmente `talvoa_restore_m99`, usando `pg_restore --no-owner --no-acl` e conexão explícita a loopback. Conferir schema, tabelas e contagens com `backend/scripts/talvoa_supritech_verify_restore.py` após inspecionar seu contrato e qualquer efeito; comparar com inventário conhecido. **Nunca** apontar `pg_restore` para Render ou Neon.
7. Remover com segurança o dump plaintext temporário e sua cópia parcial; preservar o arquivo criptografado. Registrar no Issue #99 **apenas** hashes, tamanhos, quantidade de tabelas, totais de linhas e sucesso/falha, sem valores reais, senhas ou dados pessoais. Não marcar concluído até restore real testado.

## Limites
- Não apagar backup criptografado do OneDrive, nem colocar arquivo cifrado ou plaintext no GitHub.
- Não inserir a frase secreta em chat, argumentos de processo, URL ou log.
- Não alterar variáveis de produção, banco Render, Neon, firewall, serviço de agente nem credenciais.
- O usuário autorizou restauração **isolada**, mas instalação de novos serviços ou alteração persistente de máquina deve ser claramente apresentada antes.
- A instância Render Free de origem expira em **13/11/2026 17:38:52 UTC**. Manter arquivo cifrado e chave em locais independentes.
- O Codex desktop/local só consegue ver os arquivos e programas da **máquina/perfil atual**. O ChatGPT acessa o código no GitHub, mas não controla essa sessão diretamente.
