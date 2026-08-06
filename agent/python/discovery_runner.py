from __future__ import annotations

import argparse
import ipaddress
import json
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

CURRENT_DIR = Path(__file__).resolve().parent

if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from network_manager import get_authorized_networks
except ImportError as error:
    print("ERRO: não foi possível carregar network_manager.py")
    print(f"Detalhes: {error}")
    sys.exit(1)


PRINTER_PORTS = {
    9100: "RAW/JetDirect",
    515: "LPD",
    631: "IPP",
    80: "HTTP",
    443: "HTTPS",
}

STRONG_PRINTER_PORTS = {9100, 515, 631}


@dataclass
class DiscoveredDevice:
    ip_address: str
    network: str
    open_ports: list[int]
    protocols: list[str]
    hostname: str | None
    possible_printer: bool
    confidence_score: int
    response_time_ms: int | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def check_tcp_port(
    ip_address: str,
    port: int,
    timeout: float,
) -> tuple[bool, int | None]:
    start_time = time.perf_counter()

    try:
        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM,
        ) as client:
            client.settimeout(timeout)

            result = client.connect_ex(
                (ip_address, port)
            )

            elapsed = int(
                (time.perf_counter() - start_time) * 1000
            )

            return result == 0, elapsed

    except OSError:
        return False, None


def resolve_hostname(
    ip_address: str,
    timeout: float = 0.5,
) -> str | None:
    original_timeout = socket.getdefaulttimeout()

    try:
        socket.setdefaulttimeout(timeout)
        hostname, _, _ = socket.gethostbyaddr(ip_address)
        return hostname

    except (socket.herror, socket.gaierror, TimeoutError, OSError):
        return None

    finally:
        socket.setdefaulttimeout(original_timeout)


def calculate_confidence_score(
    open_ports: list[int],
) -> int:
    score = 0

    if 9100 in open_ports:
        score += 60

    if 515 in open_ports:
        score += 45

    if 631 in open_ports:
        score += 45

    if 80 in open_ports:
        score += 10

    if 443 in open_ports:
        score += 10

    return min(score, 100)


def scan_host(
    ip_address: str,
    network: str,
    timeout: float,
    resolve_names: bool,
) -> DiscoveredDevice | None:
    open_ports: list[int] = []
    response_times: list[int] = []

    for port in PRINTER_PORTS:
        is_open, response_time = check_tcp_port(
            ip_address=ip_address,
            port=port,
            timeout=timeout,
        )

        if is_open:
            open_ports.append(port)

            if response_time is not None:
                response_times.append(response_time)

    if not open_ports:
        return None

    possible_printer = bool(
        STRONG_PRINTER_PORTS.intersection(open_ports)
    )

    confidence_score = calculate_confidence_score(
        open_ports=open_ports
    )

    hostname = None

    if resolve_names:
        hostname = resolve_hostname(ip_address)

    protocols = [
        PRINTER_PORTS[port]
        for port in open_ports
    ]

    average_response_time = None

    if response_times:
        average_response_time = int(
            sum(response_times) / len(response_times)
        )

    return DiscoveredDevice(
        ip_address=ip_address,
        network=network,
        open_ports=sorted(open_ports),
        protocols=protocols,
        hostname=hostname,
        possible_printer=possible_printer,
        confidence_score=confidence_score,
        response_time_ms=average_response_time,
    )


def generate_hosts(
    cidr: str,
    maximum_hosts: int,
) -> list[str]:
    network = ipaddress.ip_network(
        cidr,
        strict=False,
    )

    hosts: list[str] = []

    for index, host in enumerate(network.hosts()):
        if index >= maximum_hosts:
            break

        hosts.append(str(host))

    return hosts


def scan_network(
    cidr: str,
    timeout: float,
    workers: int,
    maximum_hosts: int,
    resolve_names: bool,
) -> list[DiscoveredDevice]:
    hosts = generate_hosts(
        cidr=cidr,
        maximum_hosts=maximum_hosts,
    )

    devices: list[DiscoveredDevice] = []

    print()
    print(f"Escaneando rede: {cidr}")
    print(f"Endereços analisados: {len(hosts)}")

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:
        future_map = {
            executor.submit(
                scan_host,
                ip_address,
                cidr,
                timeout,
                resolve_names,
            ): ip_address
            for ip_address in hosts
        }

        completed = 0
        total = len(future_map)

        for future in as_completed(future_map):
            completed += 1

            try:
                device = future.result()

                if device is not None:
                    devices.append(device)

                    classification = (
                        "POSSÍVEL IMPRESSORA"
                        if device.possible_printer
                        else "DISPOSITIVO WEB"
                    )

                    print(
                        f"[ENCONTRADO] {device.ip_address} | "
                        f"{classification} | "
                        f"Portas: {device.open_ports} | "
                        f"Confiança: {device.confidence_score}%"
                    )

            except Exception as error:
                ip_address = future_map[future]

                print(
                    f"[AVISO] Falha ao consultar "
                    f"{ip_address}: {error}"
                )

            if completed % 50 == 0 or completed == total:
                percentage = int(
                    completed * 100 / total
                )

                print(
                    f"Progresso: {completed}/{total} "
                    f"({percentage}%)"
                )

    return sorted(
        devices,
        key=lambda item: (
            not item.possible_printer,
            ipaddress.ip_address(item.ip_address),
        ),
    )


def save_results(
    devices: list[DiscoveredDevice],
    output_file: Path,
) -> None:
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = {
        "total_devices": len(devices),
        "possible_printers": sum(
            1
            for device in devices
            if device.possible_printer
        ),
        "devices": [
            device.to_dict()
            for device in devices
        ],
    }

    output_file.write_text(
        json.dumps(
            content,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def print_networks(networks: list[Any]) -> None:
    print()
    print("REDES AUTORIZADAS")
    print("-" * 72)

    for network in networks:
        print(
            f"Interface: {network.interface} | "
            f"Rede: {network.cidr} | "
            f"IP local: {network.ip_address}"
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PRINTFLOW Agent - Descoberta automática "
            "de redes e impressoras"
        )
    )

    parser.add_argument(
        "--network",
        action="append",
        default=[],
        help=(
            "Rede adicional em formato CIDR. "
            "Exemplo: --network 192.168.1.0/24"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=0.35,
        help="Tempo máximo por porta, em segundos.",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=100,
        help="Quantidade de verificações simultâneas.",
    )

    parser.add_argument(
        "--max-hosts",
        type=int,
        default=1024,
        help="Limite de IPs analisados por rede.",
    )

    parser.add_argument(
        "--resolve-names",
        action="store_true",
        help="Tenta descobrir o nome de cada equipamento.",
    )

    parser.add_argument(
        "--output",
        default="agent/python/output/discovery_results.json",
        help="Arquivo JSON onde o resultado será salvo.",
    )

    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()

    print("=" * 72)
    print("PRINTFLOW AGENT — DISCOVERY ENGINE")
    print("=" * 72)

    try:
        networks = get_authorized_networks(
            manual_networks=arguments.network,
            maximum_hosts=arguments.max_hosts,
        )

    except ValueError as error:
        print(f"ERRO DE CONFIGURAÇÃO: {error}")
        return 1

    if not networks:
        print()
        print("Nenhuma rede autorizada foi encontrada.")
        print(
            "Você pode informar uma rede manualmente:"
        )
        print(
            "python3 agent/python/discovery_runner.py "
            "--network 192.168.1.0/24"
        )
        return 1

    print_networks(networks)

    all_devices: list[DiscoveredDevice] = []
    scanned_networks: set[str] = set()

    for network in networks:
        if network.cidr in scanned_networks:
            continue

        scanned_networks.add(network.cidr)

        devices = scan_network(
            cidr=network.cidr,
            timeout=arguments.timeout,
            workers=arguments.workers,
            maximum_hosts=arguments.max_hosts,
            resolve_names=arguments.resolve_names,
        )

        all_devices.extend(devices)

    unique_devices: dict[str, DiscoveredDevice] = {}

    for device in all_devices:
        current = unique_devices.get(
            device.ip_address
        )

        if (
            current is None
            or device.confidence_score
            > current.confidence_score
        ):
            unique_devices[device.ip_address] = device

    final_devices = sorted(
        unique_devices.values(),
        key=lambda item: ipaddress.ip_address(
            item.ip_address
        ),
    )

    possible_printers = [
        device
        for device in final_devices
        if device.possible_printer
    ]

    output_file = Path(arguments.output)

    save_results(
        devices=final_devices,
        output_file=output_file,
    )

    print()
    print("=" * 72)
    print("RESULTADO DA DESCOBERTA")
    print("=" * 72)
    print(
        f"Redes escaneadas      : "
        f"{len(scanned_networks)}"
    )
    print(
        f"Dispositivos encontrados: "
        f"{len(final_devices)}"
    )
    print(
        f"Possíveis impressoras : "
        f"{len(possible_printers)}"
    )
    print(
        f"Resultado salvo em    : "
        f"{output_file}"
    )

    if possible_printers:
        print()
        print("POSSÍVEIS IMPRESSORAS")
        print("-" * 72)

        for printer in possible_printers:
            print(
                f"{printer.ip_address} | "
                f"Portas: {printer.open_ports} | "
                f"Protocolos: {', '.join(printer.protocols)} | "
                f"Confiança: {printer.confidence_score}%"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
