from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
import time
from pathlib import Path
from typing import Any

from api.client import PrintflowApiClient
from config.settings import AgentSettings
from discovery_runner import scan_network
from network_manager import get_authorized_networks
from snmp.engine import collect_printer_intelligence


def _monotonic() -> float:
    return time.monotonic()


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

        self.api_client = PrintflowApiClient(
            api_url=settings.api_url,
            agent_token=settings.agent_token,
            logger=logger,
            queue_directory=(
                settings.output_directory
                / "api_queue"
            ),
        )

    def _send_heartbeat_safe(
        self,
        *,
        status: str,
        error: str | None = None,
        inventory_complete: bool | None = None,
        observed_printer_ips: list[str] | None = None,
    ) -> bool:
        """
        Heartbeat é telemetria de disponibilidade e nunca deve
        interromper um ciclo local de coleta.

        Em indisponibilidade temporária da API, o Agent continua
        descobrindo, consultando SNMP e persistindo o inventário.
        """
        payload: dict[str, Any] = {
            "agent_name": self.settings.agent_name,
            "agent_version": self.settings.agent_version,
            "status": status,
        }

        if error is not None:
            payload["error"] = error

        if inventory_complete is not None:
            payload["inventory_complete"] = inventory_complete

        if observed_printer_ips is not None:
            payload["observed_printer_ips"] = observed_printer_ips

        try:
            sent = self.api_client.send_heartbeat(**payload)
        except Exception as heartbeat_error:
            self.logger.warning(
                "Heartbeat não enviado (%s): %s",
                status,
                heartbeat_error,
            )
            return False

        if sent is False:
            self.logger.warning(
                "Heartbeat não confirmado pela API (%s).",
                status,
            )
            return False

        return True

    def _write_local_health(
        self,
        *,
        status: str,
        cycle_started_monotonic: float,
        printers_count: int = 0,
        api_failed: int = 0,
        error: str | None = None,
    ) -> None:
        try:
            self.settings.output_directory.mkdir(
                parents=True,
                exist_ok=True,
            )
            health_path = (
                self.settings.output_directory
                / "agent_health.json"
            )
            payload = {
                "status": status,
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "cycle_duration_seconds": round(
                    max(
                        _monotonic()
                        - cycle_started_monotonic,
                        0.0,
                    ),
                    2,
                ),
                "printers_count": printers_count,
                "api_failed": api_failed,
                "agent_version": self.settings.agent_version,
            }
            if error:
                payload["error"] = error

            health_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except Exception as health_error:
            self.logger.warning(
                "Não foi possível atualizar agent_health.json: %s",
                health_error,
            )

    def discover_devices(self) -> list[Any]:
        """
        PRINTFLOW SAFE DISCOVERY #17

        Prioridade:
        1 - Impressoras/portas TCP-IP conhecidas pelo Windows.
        2 - Validacao somente dos IPs candidatos.
        3 - Discovery de rede atual somente como fallback.
        """

        from discovery.safe_windows import (
            discover_windows_printer_candidates,
        )

        discovered_devices: dict[str, Any] = {}

        candidates = discover_windows_printer_candidates()

        if candidates:
            self.logger.info(
                "SAFE DISCOVERY: %s candidato(s) encontrado(s) no Windows.",
                len(candidates),
            )

            def validate_candidate(candidate):
                self.logger.info(
                    "SAFE DISCOVERY: verificando %s - porta %s.",
                    candidate.ip_address,
                    candidate.port_name,
                )
                return scan_network(
                    cidr=f"{candidate.ip_address}/32",
                    timeout=self.settings.network_timeout,
                    workers=1,
                    maximum_hosts=1,
                    resolve_names=True,
                )

            candidate_workers = min(
                max(len(candidates), 1),
                12,
            )
            with ThreadPoolExecutor(
                max_workers=candidate_workers
            ) as executor:
                futures = [
                    executor.submit(
                        validate_candidate,
                        candidate,
                    )
                    for candidate in candidates
                ]
                for future in as_completed(futures):
                    for device in future.result():
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

            self.logger.info(
                "SAFE DISCOVERY: %s candidato(s) responderam.",
                len(discovered_devices),
            )


        self.logger.info(
            "SAFE DISCOVERY V3.4: complementando candidatos Windows com "
            "discovery automatico das redes autorizadas."
        )

        networks = get_authorized_networks(
            manual_networks=self.manual_networks,
            maximum_hosts=self.settings.maximum_hosts,
        )

        self.logger.info(
            "%s rede(s) autorizada(s).",
            len(networks),
        )

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

        return list(discovered_devices.values())

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

        snmp_workers = min(
            max(len(possible_printers), 1),
            8,
        )
        semaphore = asyncio.Semaphore(snmp_workers)

        async def collect_one(device):
            async with semaphore:
                self.logger.info(
                    "Consultando SNMP em %s.",
                    device.ip_address,
                )

                try:
                    snmp_result = await collect_printer_intelligence(
                        ip_address=device.ip_address,
                        community=self.settings.snmp_community,
                        timeout=self.settings.snmp_timeout,
                        retries=self.settings.snmp_retries,
                    )
                except Exception as snmp_error:
                    self.logger.exception(
                        "SNMP %s: FALHA ISOLADA | %s",
                        device.ip_address,
                        snmp_error,
                    )
                    snmp_result = {
                        "snmp_online": False,
                        "erro": str(snmp_error),
                        "dados": {},
                    }

                if snmp_result.get("snmp_online"):
                    dados = snmp_result.get("dados") or {}

                    self.logger.info(
                        "SNMP %s: OK | Fabricante=%s | Modelo=%s | "
                        "Serial=%s | Contador=%s | Origem=%s | Toner=%s%%",
                        device.ip_address,
                        dados.get("fabricante"),
                        dados.get("modelo"),
                        dados.get("serial"),
                        dados.get("contador_paginas"),
                        dados.get("contador_origem"),
                        dados.get("toner_percentual"),
                    )
                else:
                    self.logger.warning(
                        "SNMP %s: SEM RESPOSTA | Erro=%s",
                        device.ip_address,
                        snmp_result.get("erro"),
                    )

                return {
                    "discovery": asdict(device),
                    "snmp": snmp_result,
                }

        if possible_printers:
            inventory = list(
                await asyncio.gather(
                    *(
                        collect_one(device)
                        for device in possible_printers
                    )
                )
            )

        return inventory

    def save_inventory(
        self,
        devices: list[Any],
        printers: list[dict[str, Any]],
        api_result: dict[str, Any],
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
                "api_success": api_result.get(
                    "success",
                    0,
                ),
                "api_failed": api_result.get(
                    "failed",
                    0,
                ),
                "api_skipped": api_result.get(
                    "skipped",
                    0,
                ),
            },
            "devices": [
                asdict(device)
                for device in devices
            ],
            "printers": printers,
            "api_sync": api_result,
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

    def synchronize_api(
        self,
        printers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.api_client.is_configured:
            self.logger.warning(
                "PRINTFLOW_AGENT_TOKEN não configurado. "
                "Inventário será mantido apenas localmente."
            )
            return {
                "success": 0,
                "failed": 0,
                "skipped": len(printers),
                "details": [],
            }

        try:
            queue_result = self.api_client.retry_queue()
        except Exception as queue_error:
            self.logger.warning(
                "Fila pendente não pôde ser processada agora: %s",
                queue_error,
            )
            queue_result = {
                "processed": 0,
                "success": 0,
                "failed": 0,
            }

        if queue_result["processed"]:
            self.logger.info(
                "Fila anterior: %s processado(s), "
                "%s enviado(s), %s falha(s).",
                queue_result["processed"],
                queue_result["success"],
                queue_result["failed"],
            )

        try:
            result = self.api_client.send_inventory(
                printers=printers
            )
        except Exception as api_error:
            self.logger.exception(
                "Falha global de sincronização com a API: %s",
                api_error,
            )
            return {
                "success": 0,
                "failed": len(printers),
                "skipped": 0,
                "details": [
                    {
                        "success": False,
                        "message": str(api_error),
                    }
                ],
            }

        self.logger.info(
            "Sincronização API: %s sucesso(s), "
            "%s falha(s), %s ignorado(s).",
            result["success"],
            result["failed"],
            result["skipped"],
        )

        for detail in result.get("details", []):
            if detail.get("success"):
                continue

            ip_address = (
                detail.get("ip")
                or detail.get("ip_address")
                or detail.get("host")
                or "IP desconhecido"
            )
            status_code = detail.get("status_code")
            message = detail.get("message") or "Sem mensagem da API"

            self.logger.error(
                "FALHA API | IP: %s | HTTP: %s | Motivo: %s",
                ip_address,
                status_code if status_code is not None else "SEM RESPOSTA",
                message,
            )

        return result

    def run_cycle(self) -> int:
        cycle_started_monotonic = _monotonic()

        self.logger.info(
            "Iniciando ciclo do PRINTFLOW Agent."
        )

        self._send_heartbeat_safe(
            status="running",
        )

        try:
            devices = self.discover_devices()
            printers = asyncio.run(
                self.collect_snmp_data(devices)
            )
            api_result = self.synchronize_api(
                printers=printers
            )
            output_file = self.save_inventory(
                devices=devices,
                printers=printers,
                api_result=api_result,
            )
        except Exception as error:
            self._send_heartbeat_safe(
                status="error",
                error=str(error),
            )
            self._write_local_health(
                status="error",
                cycle_started_monotonic=cycle_started_monotonic,
                error=str(error),
            )
            self.logger.exception("Falha no ciclo do PRINTFLOW Agent.")
            return 1

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

        cycle_duration_seconds = max(
            _monotonic() - cycle_started_monotonic,
            0.0,
        )
        cycle_sla_seconds = max(
            int(getattr(self.settings, "cycle_sla_seconds", 90)),
            1,
        )
        cycle_status = (
            "slow"
            if cycle_duration_seconds > cycle_sla_seconds
            else "healthy"
        )

        if cycle_status == "slow":
            self.logger.warning(
                "CICLO LENTO | duração=%.2fs | SLA=%ss",
                cycle_duration_seconds,
                cycle_sla_seconds,
            )

        self._send_heartbeat_safe(
            status=cycle_status,
            inventory_complete=True,
            observed_printer_ips=[
                str(printer.get("discovery", {}).get("ip_address", ""))
                for printer in printers
                if printer.get("discovery", {}).get("ip_address")
            ],
        )

        self._write_local_health(
            status=cycle_status,
            cycle_started_monotonic=cycle_started_monotonic,
            printers_count=len(printers),
            api_failed=int(api_result.get("failed", 0)),
        )

        return 0
