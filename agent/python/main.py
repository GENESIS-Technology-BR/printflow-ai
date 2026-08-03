import json
import socket
import sys
from datetime import datetime, timezone

from api import send_printer
from config import (
    API_URL,
    MANUFACTURER,
    MODEL,
    PRINTER_IP,
    PRINTER_NAME,
    TIMEOUT,
)
from discovery import ping, test_http
from snmp import collect_snmp


def main() -> int:
    print("=" * 60)
    print("GENESIS Agent v0.2")
    print("=" * 60)
    print(f"API: {API_URL}")
    print(f"Impressora: {PRINTER_NAME}")
    print(f"IP: {PRINTER_IP}")
    print()

    print("[1/3] Testando conectividade...")
    ping_ok = ping(PRINTER_IP)
    http_ok = test_http(PRINTER_IP, TIMEOUT)

    if not ping_ok and not http_ok:
        print("ERRO: impressora offline ou inacessível.")
        return 1

    print(f"Ping: {'OK' if ping_ok else 'não respondeu'}")
    print(f"HTTP: {'OK' if http_ok else 'não respondeu'}")

    print("[2/3] Coletando informações...")
    snmp_data = collect_snmp(PRINTER_IP)

    payload = {
        "ip": PRINTER_IP,
        "name": PRINTER_NAME,
        "manufacturer": MANUFACTURER,
        "model": MODEL,
        "status": "online",
        "source": "genesis-agent-python",
        "page_count": snmp_data.get("page_count"),
    }

    print(json.dumps(payload, indent=2, ensure_ascii=False))

    print("[3/3] Enviando para a nuvem...")
    try:
        result = send_printer(API_URL, payload)
    except Exception as error:
        print(f"ERRO ao enviar para a API: {error}")
        return 2

    print("SUCESSO: impressora registrada.")
    print(f"Resposta: {json.dumps(result, ensure_ascii=False)}")
    print(f"Computador: {socket.gethostname()}")
    print(f"Horário UTC: {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
