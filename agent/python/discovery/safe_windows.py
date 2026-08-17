from __future__ import annotations

import ipaddress
import json
import platform
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowsPrinterCandidate:
    ip_address: str
    port_name: str
    source: str = "windows-print-port"


def _valid_private_ipv4(value: str | None) -> str | None:
    if not value:
        return None

    value = str(value).strip()

    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return None

    if not isinstance(ip, ipaddress.IPv4Address):
        return None

    if not ip.is_private:
        return None

    if (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return None

    return str(ip)


def discover_windows_printer_candidates() -> list[WindowsPrinterCandidate]:
    # Consulta somente as portas de impressao que o Windows ja conhece.
    # Esta funcao NAO realiza varredura da rede.

    if platform.system().lower() != "windows":
        return []

    powershell = '''
$ErrorActionPreference = "SilentlyContinue"

$items = @()

Get-PrinterPort | ForEach-Object {
    $hostAddress = $_.PrinterHostAddress

    if ($hostAddress) {
        $items += [PSCustomObject]@{
            Name = $_.Name
            PrinterHostAddress = $hostAddress
        }
    }
}

$items | ConvertTo-Json -Compress
'''

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                powershell,
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    if result.returncode != 0:
        return []

    raw = result.stdout.strip()

    if not raw:
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if isinstance(data, dict):
        data = [data]

    candidates = {}

    for item in data:
        if not isinstance(item, dict):
            continue

        ip_address = _valid_private_ipv4(
            item.get("PrinterHostAddress")
        )

        if not ip_address:
            continue

        port_name = str(
            item.get("Name") or ip_address
        ).strip()

        candidates[ip_address] = WindowsPrinterCandidate(
            ip_address=ip_address,
            port_name=port_name,
        )

    return sorted(
        candidates.values(),
        key=lambda candidate: tuple(
            int(part)
            for part in candidate.ip_address.split(".")
        ),
    )
