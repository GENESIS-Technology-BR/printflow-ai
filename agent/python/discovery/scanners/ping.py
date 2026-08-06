import ipaddress
import platform
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed


COMMON_PORTS = (80, 443, 161, 515, 631, 9100)


def icmp_ping(ip: str) -> bool:
    ping_command = shutil.which("ping")

    if not ping_command:
        return False

    system = platform.system().lower()

    if system == "windows":
        command = [ping_command, "-n", "1", "-w", "700", ip]
    else:
        command = [ping_command, "-c", "1", "-W", "1", ip]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def tcp_probe(ip: str) -> bool:
    for port in COMMON_PORTS:
        try:
            with socket.create_connection((ip, port), timeout=0.35):
                return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            continue

    return False


def host_is_alive(ip: str) -> bool:
    return icmp_ping(ip) or tcp_probe(ip)


def scan(network: str, max_workers: int = 64) -> list[str]:
    subnet = ipaddress.ip_network(network, strict=False)
    hosts = [str(ip) for ip in subnet.hosts()]
    alive: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(host_is_alive, ip): ip
            for ip in hosts
        }

        for future in as_completed(futures):
            ip = futures[future]

            try:
                if future.result():
                    alive.append(ip)
            except Exception:
                continue

    return sorted(alive, key=ipaddress.ip_address)


if __name__ == "__main__":
    test_network = "10.0.13.0/24"

    print(f"Analisando rede: {test_network}")
    hosts = scan(test_network)

    print(f"Hosts encontrados: {len(hosts)}")

    for host in hosts:
        print(host)
