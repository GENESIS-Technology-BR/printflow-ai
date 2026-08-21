from __future__ import annotations

from .scanner import scan_network
from .fingerprint import is_printer


def discover_network():

    print("=" * 50)
    print("PRINTFLOW Discovery Engine")
    print("=" * 50)

    hosts = scan_network()

    print(f"Hosts encontrados: {len(hosts)}")

    printers = []

    for host in hosts:

        if is_printer(host):

            printers.append(host)

            print(f"[PRINTER] {host}")

    print()

    print(f"Impressoras encontradas: {len(printers)}")

    return printers