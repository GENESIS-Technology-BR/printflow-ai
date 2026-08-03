import ipaddress
import json
import platform
import socket
import subprocess
from dataclasses import asdict, dataclass


@dataclass
class NetworkInfo:
    operating_system: str
    interface: str
    ip_address: str
    prefix_length: int
    network: str
    gateway: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _run(command: list[str]) -> str:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _detect_windows() -> NetworkInfo | None:
    script = r"""
$cfg = Get-NetIPConfiguration |
    Where-Object {
        $_.IPv4Address -and
        $_.NetAdapter.Status -eq 'Up' -and
        $_.InterfaceAlias -notmatch 'Loopback|Bluetooth|VPN'
    } |
    Select-Object -First 1

if ($cfg) {
    $ip = $cfg.IPv4Address.IPAddress
    $prefix = $cfg.IPv4Address.PrefixLength
    $gateway = $cfg.IPv4DefaultGateway.NextHop

    [PSCustomObject]@{
        interface = $cfg.InterfaceAlias
        ip = $ip
        prefix = $prefix
        gateway = $gateway
    } | ConvertTo-Json -Compress
}
"""
    output = _run([
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ])

    if not output:
        return None

    data = json.loads(output)
    ip_address = data["ip"]
    prefix = int(data["prefix"])
    network = str(
        ipaddress.ip_network(f"{ip_address}/{prefix}", strict=False)
    )

    return NetworkInfo(
        operating_system="Windows",
        interface=data.get("interface", "Ethernet"),
        ip_address=ip_address,
        prefix_length=prefix,
        network=network,
        gateway=data.get("gateway"),
    )


def _detect_linux() -> NetworkInfo | None:
    output = _run(["ip", "-j", "address", "show", "up"])

    if not output:
        return None

    interfaces = json.loads(output)

    for interface in interfaces:
        name = interface.get("ifname", "")

        if name == "lo":
            continue

        for address in interface.get("addr_info", []):
            if (
                address.get("family") == "inet"
                and address.get("scope") == "global"
            ):
                ip_address = address["local"]
                prefix = int(address["prefixlen"])
                network = str(
                    ipaddress.ip_network(
                        f"{ip_address}/{prefix}",
                        strict=False,
                    )
                )

                return NetworkInfo(
                    operating_system="Linux",
                    interface=name,
                    ip_address=ip_address,
                    prefix_length=prefix,
                    network=network,
                )

    return None


def _detect_macos() -> NetworkInfo | None:
    interface = _run(["route", "get", "default"])

    active_interface = None
    gateway = None

    for line in interface.splitlines():
        line = line.strip()

        if line.startswith("interface:"):
            active_interface = line.split(":", 1)[1].strip()

        if line.startswith("gateway:"):
            gateway = line.split(":", 1)[1].strip()

    if not active_interface:
        return None

    ip_address = _run(["ipconfig", "getifaddr", active_interface])

    if not ip_address:
        return None

    # Inicialmente usamos /24 como fallback seguro no macOS.
    prefix = 24
    network = str(
        ipaddress.ip_network(f"{ip_address}/{prefix}", strict=False)
    )

    return NetworkInfo(
        operating_system="macOS",
        interface=active_interface,
        ip_address=ip_address,
        prefix_length=prefix,
        network=network,
        gateway=gateway,
    )


def _detect_fallback() -> NetworkInfo:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect(("8.8.8.8", 80))
        ip_address = sock.getsockname()[0]
    except OSError:
        ip_address = "127.0.0.1"
    finally:
        sock.close()

    prefix = 24
    network = str(
        ipaddress.ip_network(f"{ip_address}/{prefix}", strict=False)
    )

    return NetworkInfo(
        operating_system=platform.system() or "Unknown",
        interface="automatic",
        ip_address=ip_address,
        prefix_length=prefix,
        network=network,
    )


def detect_active_network() -> NetworkInfo:
    system = platform.system().lower()

    try:
        if system == "windows":
            detected = _detect_windows()
        elif system == "linux":
            detected = _detect_linux()
        elif system == "darwin":
            detected = _detect_macos()
        else:
            detected = None

        return detected or _detect_fallback()

    except Exception:
        return _detect_fallback()


def limited_discovery_network(info: NetworkInfo) -> ipaddress.IPv4Network:
    """
    Evita uma varredura agressiva em redes muito grandes.

    Exemplo:
    Rede real: 10.2.0.0/16
    Descoberta inicial: bloco /24 onde o Agent está instalado.
    """
    full_network = ipaddress.ip_network(info.network, strict=False)

    if full_network.prefixlen < 24:
        return ipaddress.ip_network(
            f"{info.ip_address}/24",
            strict=False,
        )

    return full_network
