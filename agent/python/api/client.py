from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class ApiSyncResult:
    success: bool
    status_code: int | None
    message: str
    response_data: dict[str, Any] | list[Any] | None = None


class PrintflowApiClient:
    def __init__(
        self,
        api_url: str,
        agent_token: str,
        logger: logging.Logger,
        queue_directory: Path,
        timeout_seconds: float = 30.0,
        retries: int = 2,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.agent_token = agent_token.strip()
        self.logger = logger
        self.queue_directory = queue_directory
        self.timeout_seconds = timeout_seconds
        self.retries = max(retries, 0)

        self.printers_endpoint = (
            f"{self.api_url}/api/v1/printers/agent"
        )

        self.queue_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    @property
    def is_configured(self) -> bool:
        return bool(
            self.api_url
            and self.agent_token
        )

    def health_check(self) -> bool:
        try:
            response = requests.get(
                self.printers_endpoint,
                timeout=self.timeout_seconds,
            )

            return response.status_code < 500

        except requests.RequestException:
            return False

    def build_payload(
        self,
        printer: dict[str, Any],
    ) -> dict[str, Any]:
        discovery = printer.get(
            "discovery",
            {},
        )

        snmp = printer.get(
            "snmp",
            {},
        )

        snmp_data = snmp.get(
            "dados",
            {},
        )

        ip_address = (
            discovery.get("ip_address")
            or printer.get("ip")
            or ""
        )

        description = (
            snmp_data.get("descricao")
            or ""
        )

        hostname = (
            discovery.get("hostname")
            or snmp_data.get("nome")
            or ""
        )

        # ----------------------------------------------------
        # MODELO
        # Prioriza a inteligência do motor SNMP.
        # ----------------------------------------------------
        model = (
            snmp_data.get("modelo")
            or self._detect_model(
                description=description,
                fallback=printer.get("model"),
            )
        )

        # ----------------------------------------------------
        # FABRICANTE
        # Prioriza a inteligência do motor SNMP.
        # ----------------------------------------------------
        manufacturer = (
            snmp_data.get("fabricante")
            or self._detect_manufacturer(
                description=description,
                model=model,
            )
        )

        # ----------------------------------------------------
        # CONTADOR
        # ----------------------------------------------------
        page_count = self._parse_integer(
            snmp_data.get("contador_paginas")
        )

        # ----------------------------------------------------
        # SERIAL
        # ----------------------------------------------------
        serial = snmp_data.get("serial")

        if serial is not None:
            serial = str(serial).strip() or None

        # ----------------------------------------------------
        # TONER / HEALTH
        # ----------------------------------------------------
        toner_percent = self._parse_integer(
            snmp_data.get("toner_percentual")
        )

        health_score = self._parse_integer(
            snmp_data.get("health_score")
        )

        health_status = snmp_data.get(
            "health_status"
        )

        if health_status is not None:
            health_status = (
                str(health_status).strip()
                or None
            )

        # ----------------------------------------------------
        # STATUS REAL
        # Antes o Agent enviava "online" nos dois casos.
        # ----------------------------------------------------
        status = (
            "online"
            if snmp.get("snmp_online")
            else "offline"
        )

        # ----------------------------------------------------
        # NOME
        # Prioriza hostname e modelo real.
        # ----------------------------------------------------
        name = (
            snmp_data.get("display_name")
            or hostname
            or model
            or f"Impressora {ip_address}"
        )

        return {
            "ip": ip_address,
            "name": str(name)[:150],
            "manufacturer": (
                str(manufacturer)[:100]
                if manufacturer
                else None
            ),
            "model": (
                str(model)[:180]
                if model
                else None
            ),
            "serial": (
                str(serial)[:180]
                if serial
                else None
            ),
            "status": status,
            "source": "agent",
            "page_count": page_count,
            "toner_percent": toner_percent,
            "health_score": health_score,
            "health_status": (
                str(health_status)[:30]
                if health_status
                else None
            ),
            "agent_token": self.agent_token,
        }

    def send_printer(
        self,
        printer: dict[str, Any],
        save_on_failure: bool = True,
    ) -> ApiSyncResult:
        if not self.is_configured:
            return ApiSyncResult(
                success=False,
                status_code=None,
                message=(
                    "Agent Token não configurado. "
                    "Sincronização ignorada."
                ),
            )

        payload = self.build_payload(
            printer=printer
        )

        if not payload["ip"]:
            return ApiSyncResult(
                success=False,
                status_code=None,
                message=(
                    "Impressora sem endereço IP. "
                    "Registro ignorado."
                ),
            )

        last_error = "Falha desconhecida."

        for attempt in range(
            self.retries + 1
        ):
            try:
                self.logger.info(
                    "Enviando impressora %s para a API. "
                    "Tentativa %s/%s.",
                    payload["ip"],
                    attempt + 1,
                    self.retries + 1,
                )

                response = requests.post(
                    self.printers_endpoint,
                    json=payload,
                    timeout=self.timeout_seconds,
                )

                response_data = self._read_response(
                    response
                )

                if response.status_code in {
                    200,
                    201,
                }:
                    return ApiSyncResult(
                        success=True,
                        status_code=response.status_code,
                        message=(
                            "Impressora sincronizada "
                            "com sucesso."
                        ),
                        response_data=response_data,
                    )

                if response.status_code == 401:
                    return ApiSyncResult(
                        success=False,
                        status_code=401,
                        message=(
                            "Agent Token inválido. "
                            "Copie novamente o token "
                            "exibido no Dashboard."
                        ),
                        response_data=response_data,
                    )

                if response.status_code == 422:
                    last_error = (
                        "A API recusou os dados da "
                        "impressora. Verifique o payload."
                    )
                    break

                # BUILD11_HTTP_DETAIL
                try:
                    response_preview = response.text[:600]
                except Exception:
                    response_preview = "<resposta indisponivel>"
                self.logger.error(
                    "Falha API | IP=%s | HTTP=%s | URL=%s | Resposta=%s",
                    payload.get("ip", "desconhecido"),
                    response.status_code,
                    self.printers_endpoint,
                    response_preview,
                )

                last_error = (
                    f"API respondeu com HTTP "
                    f"{response.status_code}."
                )

            except requests.Timeout:
                last_error = (
                    "Tempo de resposta da API excedido."
                )

            except requests.ConnectionError:
                last_error = (
                    "Não foi possível conectar à API."
                )

            except requests.RequestException as error:
                last_error = (
                    f"Falha HTTP: {error}"
                )

            if attempt < self.retries:
                time.sleep(
                    2 * (attempt + 1)
                )

        if save_on_failure:
            queue_file = self.save_to_queue(
                payload=payload,
                reason=last_error,
            )

            last_error = (
                f"{last_error} Registro salvo na fila "
                f"local: {queue_file.name}"
            )

        return ApiSyncResult(
            success=False,
            status_code=None,
            message=last_error,
        )

    def send_inventory(
        self,
        printers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = {
            "total": len(printers),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        if not printers:
            return result

        if not self.is_configured:
            result["skipped"] = len(printers)
            result["details"].append(
                {
                    "success": False,
                    "message": (
                        "PRINTFLOW_AGENT_TOKEN "
                        "não configurado."
                    ),
                }
            )
            return result

        for printer in printers:
            sync_result = self.send_printer(
                printer=printer
            )

            detail = {
                "success": sync_result.success,
                "status_code": (
                    sync_result.status_code
                ),
                "message": sync_result.message,
            }

            result["details"].append(
                detail
            )

            if sync_result.success:
                result["success"] += 1
            else:
                result["failed"] += 1

        return result

    def retry_queue(self) -> dict[str, int]:
        summary = {
            "processed": 0,
            "success": 0,
            "failed": 0,
        }

        if not self.is_configured:
            return summary

        queue_files = sorted(
            self.queue_directory.glob(
                "*.json"
            )
        )

        for queue_file in queue_files:
            summary["processed"] += 1

            try:
                content = json.loads(
                    queue_file.read_text(
                        encoding="utf-8"
                    )
                )

                payload = content.get(
                    "payload",
                    {}
                )

                response = requests.post(
                    self.printers_endpoint,
                    json=payload,
                    timeout=self.timeout_seconds,
                )

                if response.status_code in {
                    200,
                    201,
                }:
                    queue_file.unlink(
                        missing_ok=True
                    )
                    summary["success"] += 1
                else:
                    summary["failed"] += 1

            except Exception:
                summary["failed"] += 1

        return summary

    def save_to_queue(
        self,
        payload: dict[str, Any],
        reason: str,
    ) -> Path:
        timestamp = int(
            time.time() * 1000
        )

        safe_ip = str(
            payload.get(
                "ip",
                "unknown",
            )
        ).replace(".", "_")

        output_file = (
            self.queue_directory
            / f"{timestamp}_{safe_ip}.json"
        )

        content = {
            "reason": reason,
            "created_at_unix": timestamp,
            "payload": payload,
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

    @staticmethod
    def _parse_integer(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        try:
            normalized = (
                str(value)
                .replace(".", "")
                .replace(",", "")
                .strip()
            )

            return int(normalized)

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _detect_manufacturer(
        description: str,
        model: str | None,
    ) -> str | None:
        content = (
            f"{description} {model or ''}"
        ).lower()

        vendors = {
            "hewlett-packard": "HP",
            "hewlett packard": "HP",
            "hp ": "HP",
            "ricoh": "Ricoh",
            "kyocera": "Kyocera",
            "canon": "Canon",
            "brother": "Brother",
            "lexmark": "Lexmark",
            "xerox": "Xerox",
            "epson": "Epson",
            "zebra": "Zebra",
            "samsung": "Samsung",
        }

        for term, vendor in vendors.items():
            if term in content:
                return vendor

        return None

    @staticmethod
    def _detect_model(
        description: str,
        fallback: Any = None,
    ) -> str | None:
        if fallback:
            return str(fallback).strip()

        if description:
            return description.strip()

        return None

    @staticmethod
    def _read_response(
        response: requests.Response,
    ) -> dict[str, Any] | list[Any] | None:
        try:
            return response.json()
        except ValueError:
            return {
                "text": response.text[:1000]
            }
