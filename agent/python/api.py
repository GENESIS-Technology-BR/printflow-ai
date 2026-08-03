import requests


def send_printer(api_url: str, payload: dict, timeout: int = 30) -> dict:
    endpoint = f"{api_url}/api/v1/printers/agent"

    response = requests.post(
        endpoint,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()
    return response.json()
