PRINTFLOW AGENT WINDOWS - TESTE

1. Extraia todo o arquivo ZIP.
2. Não mova somente o EXE; mantenha todos os arquivos juntos.
3. Execute "Executar-PRINTFLOW-Agent.bat".
4. Informe o Token do Agent exibido no Dashboard.
5. Aguarde o escaneamento da rede.
6. Verifique o Dashboard após a conclusão.

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
