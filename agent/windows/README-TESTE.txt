PRINTFLOW AGENT WINDOWS - TESTE

1. Extraia todo o arquivo ZIP.
2. Não mova somente o EXE; mantenha todos os arquivos juntos.
3. No Dashboard, copie somente o "Token do Agent" de 43 caracteres.
4. Execute "INSTALAR-PRINTFLOW-Agent.bat" para instalar e iniciar o Agent.
5. Nao copie o token de sessao/login do navegador.
6. Aguarde o escaneamento da rede e verifique o Dashboard.

Arquivos gerados durante o teste:
- output\agent_inventory.json
- logs\printflow-agent.log
- output\api_queue\ (somente se houver falha de comunicação)

Observações:
- O computador precisa estar conectado à rede das impressoras.
- O Agent detecta automaticamente a rede local.
- Redes grandes são reduzidas inicialmente para a sub-rede /24 local.
- O SNMP deve estar habilitado nas impressoras.
- Comunidade padrão utilizada: public.
