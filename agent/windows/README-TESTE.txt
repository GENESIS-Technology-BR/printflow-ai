PRINTFLOW AGENT WINDOWS v0.3.3

ARQUITETURA
- Instalacao residente em C:\ProgramData\PRINTFLOW\Agent
- Execucao automatica como SYSTEM
- Inicializacao no boot do Windows
- Agent executado em modo --daemon
- Token protegido com DPAPI LocalMachine
- Configuracao restrita a SYSTEM e Administradores
- Discovery automatico + redes adicionais
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