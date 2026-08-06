from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import AgentSettings
from discovery_runner import scan_network
from network_manager import get_authorized_networks
from snmp_probe import collect_printer


class PrintflowAgentService:
    def __init__(
        self,
        settings: AgentSettings,
        logger: logging.Logger,
        manual_networks: list[str] | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.manual_networks = manual_networks or []

    def discover_devices(self) -> list[Any]:
        networks = get_authorized_networks(
            manual_networks=self.manual_networks,
            maximum_hosts=self.settings.maximum_hosts,
        )

        if not networks:
            self.logger.warning(
                "Nenhuma rede autorizada foi encontrada."
            )
            return []

        self.logger.info(
            "%s rede(s) autorizada(s).",
            len(networks),
        )

        discovered_devices: dict[str, Any] = {}

        for network in networks:
            self.logger.info(
                "Escaneando rede %s pela interface %s.",
                network.cidr,
                network.interface,
            )

            devices = scan_network(
                cidr=network.cidr,
                timeout=self.settings.network_timeout,
                workers=self.settings.network_workers,
                maximum_hosts=self.settings.maximum_hosts,
                resolve_names=self.settings.resolve_names,
            )

            for device in devices:
                current = discovered_devices.get(
                    device.ip_address
                )

                if (
                    current is None
                    or device.confidence_score
                    > current.confidence_score
                ):
                    discovered_devices[
                        device.ip_address
                    ] = device

        return list(
            discovered_devices.values()
        )

    async def collect_snmp_data(
        self,
        devices: list[Any],
    ) -> list[dict[str, Any]]:
        inventory: list[dict[str, Any]] = []

        possible_printers = [
            device
            for device in devices
            if device.possible_printer
        ]

        self.logger.info(
            "%s possível(is) impressora(s) encontrada(s).",
            len(possible_printers),
        )

        for device in possible_printers:
            self.logger.info(
                "Consultando SNMP em %s.",
                device.ip_address,
            )

            snmp_result = await collect_printer(
                ip_address=device.ip_address,
                community=self.settings.snmp_community,
                timeout=self.settings.snmp_timeout,
                retries=self.settings.snmp_retries,
            )

            inventory.append(
                {
                    "discovery": asdict(device),
                    "snmp": snmp_result,
                }
            )

        return inventory

    def save_inventory(
        self,
        devices: list[Any],
        printers: list[dict[str, Any]],
    ) -> Path:
        self.settings.output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file = (
            self.settings.output_directory
            / "agent_inventory.json"
        )

        content = {
            "agent": {
                "name": self.settings.agent_name,
                "version": self.settings.agent_version,
            },
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "summary": {
                "devices_found": len(devices),
                "possible_printers": len(printers),
                "snmp_online": sum(
                    1
                    for printer in printers
                    if printer["snmp"].get(
                        "snmp_online"
                    )
                ),
            },
            "devices": [
                asdict(device)
                for device in devices
            ],
            "printers": printers,
        }

        output_file.write_text(
            json.dumps(
                content,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return output_file

    def run_cycle(self) -> int:
        self.logger.info(
            "Iniciando ciclo do PRINTFLOW Agent."
        )

        devices = self.discover_devices()

        printers = asyncio.run(
            self.collect_snmp_data(devices)
        )

        output_file = self.save_inventory(
            devices=devices,
            printers=printers,
        )

        self.logger.info(
            "Ciclo finalizado."
        )

        self.logger.info(
            "Dispositivos encontrados: %s.",
            len(devices),
        )

        self.logger.info(
            "Possíveis impressoras: %s.",
            len(printers),
        )

        self.logger.info(
            "Inventário salvo em %s.",
            output_file,
        )

        return 0
