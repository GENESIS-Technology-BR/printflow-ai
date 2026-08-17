from __future__ import annotations

import ipaddress
import socket
from dataclasses import asdict, dataclass
from typing import Any

import psutil
import subprocess


BLOCKED_INTERFACE_TERMS = (
    "docker",
    "veth",
    "vmnet",
    "virtualbox",
    "loopback",
    "bluetooth",
    "npcap",
    "hyper-v",
    "wsl",
    "tailscale",
)


@dataclass
class DetectedNetwork:
    interface: str
    ip_address: str
    netmask: str
    cidr: str
    broadcast: str | None
    is_private: bool
    scan_allowed: bool
    reason: str
    original_cidr: str | None = None
    automatically_reduced: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def is_blocked_interface(interface_name: str) -> bool:
    normalized_name = interface_name.lower()

    return any(
        term in normalized_name
        for term in BLOCKED_INTERFACE_TERMS
    )


def calculate_network(
    ip_address: str,
    netmask: str,
) -> ipaddress.IPv4Network:
    network_interface = ipaddress.IPv4Interface(
        f"{ip_address}/{netmask}"
    )

    return network_interface.network


def usable_hosts(
    network: ipaddress.IPv4Network,
) -> int:
    return max(network.num_addresses - 2, 0)


def create_safe_local_subnet(
    ip_address: str,
    original_network: ipaddress.IPv4Network,
    safe_prefix: int = 24,
) -> ipaddress.IPv4Network:
    """
    Reduz automaticamente redes grandes para uma sub-rede segura
    contendo o IP atual do computador.

    Exemplo:
    IP local: 10.0.1.49
    Rede original: 10.0.0.0/16
    Rede segura: 10.0.1.0/24
    """

    if original_network.prefixlen >= safe_prefix:
        return original_network

    local_interface = ipaddress.IPv4Interface(
        f"{ip_address}/{safe_prefix}"
    )

    safe_network = local_interface.network

    if not safe_network.subnet_of(original_network):
        return original_network

    return safe_network


def prepare_detected_network(
    interface_name: str,
    ip_address: str,
    netmask: str,
    broadcast: str | None,
    maximum_hosts: int,
    safe_prefix: int,
) -> DetectedNetwork | None:
    try:
        parsed_ip = ipaddress.ip_address(ip_address)
    except ValueError:
        return None

    if not isinstance(parsed_ip, ipaddress.IPv4Address):
        return None

    if parsed_ip.is_loopback:
        return None

    if parsed_ip.is_unspecified:
        return None

    if parsed_ip.is_multicast:
        return None

    if parsed_ip.is_link_local:
        return None

    try:
        original_network = calculate_network(
            ip_address=ip_address,
            netmask=netmask,
        )
    except ValueError:
        return None

    if is_blocked_interface(interface_name):
        return DetectedNetwork(
            interface=interface_name,
            ip_address=ip_address,
            netmask=netmask,
            cidr=str(original_network),
            broadcast=broadcast,
            is_private=original_network.is_private,
            scan_allowed=False,
            reason="Interface virtual ou bloqueada.",
            original_cidr=str(original_network),
        )

    if not original_network.is_private:
        return DetectedNetwork(
            interface=interface_name,
            ip_address=ip_address,
            netmask=netmask,
            cidr=str(original_network),
            broadcast=broadcast,
            is_private=False,
            scan_allowed=False,
            reason="Rede pública bloqueada por segurança.",
            original_cidr=str(original_network),
        )

    original_hosts = usable_hosts(original_network)

    if original_hosts <= maximum_hosts:
        return DetectedNetwork(
            interface=interface_name,
            ip_address=ip_address,
            netmask=netmask,
            cidr=str(original_network),
            broadcast=str(original_network.broadcast_address),
            is_private=True,
            scan_allowed=True,
            reason="Rede liberada para descoberta.",
            original_cidr=str(original_network),
        )

    safe_network = create_safe_local_subnet(
        ip_address=ip_address,
        original_network=original_network,
        safe_prefix=safe_prefix,
    )

    safe_hosts = usable_hosts(safe_network)

    if safe_hosts > maximum_hosts:
        return DetectedNetwork(
            interface=interface_name,
            ip_address=ip_address,
            netmask=netmask,
            cidr=str(original_network),
            broadcast=str(original_network.broadcast_address),
            is_private=True,
            scan_allowed=False,
            reason=(
                "Rede muito grande e não foi possível criar "
                "uma faixa automática segura."
            ),
            original_cidr=str(original_network),
        )

    return DetectedNetwork(
        interface=interface_name,
        ip_address=ip_address,
        netmask=str(safe_network.netmask),
        cidr=str(safe_network),
        broadcast=str(safe_network.broadcast_address),
        is_private=True,
        scan_allowed=True,
        reason=(
            f"Rede original {original_network} reduzida "
            f"automaticamente para {safe_network}."
        ),
        original_cidr=str(original_network),
        automatically_reduced=True,
    )


def detect_local_networks(
    maximum_hosts: int = 1024,
    safe_prefix: int = 24,
) -> list[DetectedNetwork]:
    detected_networks: list[DetectedNetwork] = []
    unique_cidrs: set[str] = set()

    interfaces = psutil.net_if_addrs()

    for interface_name, addresses in interfaces.items():
        for address in addresses:
            if address.family != socket.AF_INET:
                continue

            if not address.address or not address.netmask:
                continue

            detected = prepare_detected_network(
                interface_name=interface_name,
                ip_address=address.address,
                netmask=address.netmask,
                broadcast=address.broadcast,
                maximum_hosts=maximum_hosts,
                safe_prefix=safe_prefix,
            )

            if detected is None:
                continue

            unique_key = (
                f"{detected.interface}:"
                f"{detected.cidr}:"
                f"{detected.scan_allowed}"
            )

            if unique_key in unique_cidrs:
                continue

            unique_cidrs.add(unique_key)
            detected_networks.append(detected)

    return sorted(
        detected_networks,
        key=lambda item: (
            not item.scan_allowed,
            item.interface.lower(),
            item.cidr,
        ),
    )


def validate_manual_network(
    cidr: str,
    maximum_hosts: int = 1024,
) -> DetectedNetwork:
    normalized_cidr = cidr.strip()

    try:
        network = ipaddress.ip_network(
            normalized_cidr,
            strict=False,
        )
    except ValueError as error:
        raise ValueError(
            f"Faixa de rede inválida: {normalized_cidr}"
        ) from error

    if not isinstance(network, ipaddress.IPv4Network):
        raise ValueError(
            "Nesta versão, informe uma rede IPv4."
        )

    if not network.is_private:
        raise ValueError(
            "O PRINTFLOW não permite escanear redes públicas."
        )

    hosts = usable_hosts(network)

    if hosts > maximum_hosts:
        raise ValueError(
            f"A rede manual {network} possui {hosts} hosts. "
            f"O limite atual é {maximum_hosts}. "
            "Informe uma faixa menor, como /24 ou /23."
        )

    return DetectedNetwork(
        interface="manual",
        ip_address=str(network.network_address),
        netmask=str(network.netmask),
        cidr=str(network),
        broadcast=str(network.broadcast_address),
        is_private=True,
        scan_allowed=True,
        reason="Rede adicionada manualmente.",
        original_cidr=str(network),
    )



def detect_routed_networks(
    maximum_hosts: int = 1024,
) -> list[str]:
    """
    Descobre redes IPv4 privadas explicitamente presentes
    na tabela de rotas do Windows.

    Regras de segurança:
    - ignora rota default;
    - ignora redes públicas;
    - ignora loopback/link-local/multicast;
    - ignora redes acima do limite maximum_hosts;
    - não expande rotas grandes em várias sub-redes;
    - remove duplicidades.

    Em sistemas onde 'route print -4' não estiver disponível,
    simplesmente retorna uma lista vazia.
    """

    try:
        resultado = subprocess.run(
            ["route", "print", "-4"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if resultado.returncode != 0:
        return []

    redes: set[str] = set()

    for linha in resultado.stdout.splitlines():
        partes = linha.split()

        # Formato esperado do Windows:
        # destino mascara gateway interface metrica
        if len(partes) < 5:
            continue

        destino = partes[0]
        mascara = partes[1]

        try:
            endereco = ipaddress.ip_address(destino)

            if not isinstance(
                endereco,
                ipaddress.IPv4Address,
            ):
                continue

            rede = ipaddress.ip_network(
                f"{destino}/{mascara}",
                strict=False,
            )

        except ValueError:
            continue

        # Rota default
        if rede.prefixlen == 0:
            continue

        # Somente redes privadas
        if not rede.is_private:
            continue

        # Redes especiais
        if (
            rede.network_address.is_loopback
            or rede.network_address.is_link_local
            or rede.network_address.is_multicast
            or rede.network_address.is_unspecified
        ):
            continue

        # Segurança: não escanear automaticamente redes enormes
        if usable_hosts(rede) > maximum_hosts:
            continue

        redes.add(str(rede))

    def chave(cidr: str):
        rede = ipaddress.ip_network(
            cidr,
            strict=False,
        )
        return (
            int(rede.network_address),
            rede.prefixlen,
        )

    return sorted(redes, key=chave)


def get_authorized_networks(
    manual_networks: list[str] | None = None,
    maximum_hosts: int = 1024,
    safe_prefix: int = 24,
) -> list[DetectedNetwork]:
    networks = detect_local_networks(
        maximum_hosts=maximum_hosts,
        safe_prefix=safe_prefix,
    )

    # ========================================================
    # MOTOR V2 - REDES ROTEADAS
    # ========================================================
    routed_cidrs = detect_routed_networks(
        maximum_hosts=maximum_hosts,
    )

    local_cidrs = {
        network.cidr
        for network in networks
    }

    for cidr in routed_cidrs:
        if cidr in local_cidrs:
            continue

        try:
            validated = validate_manual_network(
                cidr=cidr,
                maximum_hosts=maximum_hosts,
            )
        except ValueError:
            continue

        routed_network = DetectedNetwork(
            interface="rota-windows",
            ip_address=validated.ip_address,
            netmask=validated.netmask,
            cidr=validated.cidr,
            broadcast=validated.broadcast,
            is_private=True,
            scan_allowed=True,
            reason=(
                "Rede privada roteável detectada "
                "automaticamente no Windows."
            ),
            original_cidr=validated.original_cidr,
        )

        networks.append(routed_network)
        local_cidrs.add(routed_network.cidr)

    existing_cidrs = {
        network.cidr
        for network in networks
        if network.scan_allowed
    }

    if manual_networks:
        for cidr in manual_networks:
            manual_network = validate_manual_network(
                cidr=cidr,
                maximum_hosts=maximum_hosts,
            )

            if manual_network.cidr in existing_cidrs:
                continue

            networks.append(manual_network)
            existing_cidrs.add(manual_network.cidr)

    return sorted(
        [
            network
            for network in networks
            if network.scan_allowed
        ],
        key=lambda item: (
            item.interface.lower(),
            ipaddress.ip_network(item.cidr).network_address,
        ),
    )


def main() -> int:
    print("=" * 72)
    print("PRINTFLOW AGENT — DETECÇÃO INTELIGENTE DE REDES")
    print("=" * 72)

    networks = detect_local_networks()

    if not networks:
        print()
        print("Nenhuma rede IPv4 válida foi encontrada.")
        return 1

    for network in networks:
        status = (
            "AUTORIZADA"
            if network.scan_allowed
            else "IGNORADA"
        )

        print()
        print(f"Interface      : {network.interface}")
        print(f"IP local       : {network.ip_address}")
        print(f"Rede utilizada : {network.cidr}")

        if network.original_cidr != network.cidr:
            print(f"Rede original  : {network.original_cidr}")

        print(f"Máscara        : {network.netmask}")
        print(f"Broadcast      : {network.broadcast}")
        print(f"Status         : {status}")
        print(f"Motivo         : {network.reason}")

    authorized = [
        network
        for network in networks
        if network.scan_allowed
    ]

    print()
    print("=" * 72)
    print(f"Redes autorizadas: {len(authorized)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
