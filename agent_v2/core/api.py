import requests


def send_printer(api, token, printer):
    """Envia telemetria de uma impressora para a API.

    A excecao de rede e propagada para o loop principal, que registra a falha
    e continua processando os demais equipamentos sem encerrar o Agent.
    """
    return requests.post(
        f"{api.rstrip('/')}/api/v1/printers/agent",
        json={
            "agent_token": token,
            **printer,
        },
        timeout=15,
    )
