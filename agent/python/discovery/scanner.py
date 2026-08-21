from __future__ import annotations

import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor


def discover_local_network() -> ipaddress.IPv4Network:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)

    network = ipaddress.ip_network(f"{local_ip}/24", strict=False)

    return network


def ping_host(ip: str, timeout: float = 0.2) -> bool:
    COMMON_PORTS = (80, 443, 9100, 161)

    for port in COMMON_PORTS:
        try:
            with socket.create_connection((ip, port), timeout):
                return True
        except Exception:
            pass

    return False


def scan_network(max_workers: int = 100) -> list[str]:
    network = discover_local_network()

    hosts = [str(ip) for ip in network.hosts()]

    alive = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        results = executor.map(
            ping_host,
            hosts,
        )

        for host, status in zip(hosts, results):

            if status:
                alive.append(host)

    return alive