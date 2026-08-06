import requests


def send_printer(api, token, printer):

    response = requests.post(
        f"{api}/api/v1/printers/agent",
        json={
            "agent_token": token,
            **printer
        },
        timeout=15
    )

    print(
        response.status_code,
        response.text
    )

    return response
