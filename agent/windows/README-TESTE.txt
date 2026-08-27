PRINTFLOW AGENT WINDOWS v0.3.6

ARQUITETURA
- Instalacao residente em C:\ProgramData\PRINTFLOW\Agent
- Execucao automatica como SYSTEM
- Inicializacao no boot do Windows
- Agent executado em modo --daemon
- Token protegido com DPAPI LocalMachine
- Configuracao restrita a SYSTEM e Administradores
- Discovery automatico + redes adicionais
- Descoberta automatica de hostname
- Heartbeat e sincronizacao com a API

INSTALACAO
1. Extraia todo o ZIP.
2. No Dashboard PRINTFLOW abra Agents.
3. Clique em "Copiar token".
4. Execute INSTALAR-PRINTFLOW-Agent.bat.
5. Informe redes adicionais separadas por virgula.
   Exemplo:
   10.2.0.0/24,10.2.128.0/24
6. Aguarde a mensagem de instalacao concluida.
7. Confira o Dashboard.


ATUALIZACAO DE CLIENTE EXISTENTE
1. Extraia a nova Build.
2. Execute ATUALIZAR-PRINTFLOW-Agent.bat como administrador.
3. O atualizador detecta a instalacao residente.
4. Token protegido por maquina e redes sao preservados.
5. Um backup da versao anterior e criado automaticamente.
6. A nova versao e iniciada como SYSTEM.
7. Se a atualizacao falhar, o rollback automatico tenta restaurar
   a versao anterior.

IMPORTANTE
- Nao mova somente o EXE.
- Nao copie o token de sessao/login do navegador.
- O Agent continua rodando mesmo sem usuario logado.
- A reinicializacao do Windows inicia o Agent automaticamente.

PASTAS INSTALADAS
C:\ProgramData\PRINTFLOW\Agent
C:\ProgramData\PRINTFLOW\Agent\config
C:\ProgramData\PRINTFLOW\Agent\logs
C:\ProgramData\PRINTFLOW\Agent\output

ARQUIVOS DE DIAGNOSTICO
INSTALL-DIAGNOSTICO.txt
RESULTADO-VALIDACAO.txt