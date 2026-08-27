from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from version import AGENT_VERSION


if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "sim",
        "on",
    }


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)

    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class AgentSettings:
    agent_name: str
    agent_version: str

    scan_interval_seconds: int
    network_timeout: float
    network_workers: int
    maximum_hosts: int
    resolve_names: bool

    snmp_community: str
    snmp_timeout: float
    snmp_retries: int

    output_directory: Path
    logs_directory: Path

    api_url: str
    agent_token: str

    @classmethod
    def load(cls) -> "AgentSettings":
        return cls(
            agent_name=os.getenv(
                "PRINTFLOW_AGENT_NAME",
                "PRINTFLOW Agent",
            ),
            agent_version=os.getenv(
                "PRINTFLOW_AGENT_VERSION",
                AGENT_VERSION,
            ),
            scan_interval_seconds=env_int(
                "PRINTFLOW_SCAN_INTERVAL",
                900,
            ),
            network_timeout=env_float(
                "PRINTFLOW_NETWORK_TIMEOUT",
                0.35,
            ),
            network_workers=env_int(
                "PRINTFLOW_NETWORK_WORKERS",
                100,
            ),
            maximum_hosts=env_int(
                "PRINTFLOW_MAXIMUM_HOSTS",
                1024,
            ),
            resolve_names=env_bool(
                "PRINTFLOW_RESOLVE_NAMES",
                True,
            ),
            snmp_community=os.getenv(
                "PRINTFLOW_SNMP_COMMUNITY",
                "public",
            ),
            snmp_timeout=env_float(
                "PRINTFLOW_SNMP_TIMEOUT",
                1.0,
            ),
            snmp_retries=env_int(
                "PRINTFLOW_SNMP_RETRIES",
                1,
            ),
            output_directory=BASE_DIR / "output",
            logs_directory=BASE_DIR / "logs",
            api_url=os.getenv(
                "PRINTFLOW_API_URL",
                "https://printflow-api-genesis.onrender.com",
            ).rstrip("/"),
            agent_token=os.getenv(
                "PRINTFLOW_AGENT_TOKEN",
                "",
            ),
        )
