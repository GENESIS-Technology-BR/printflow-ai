from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

from pysnmp.hlapi.v3arch.asyncio import (
    CommunityData,
    ContextData,
    ObjectIdentity,
    ObjectType,
    SnmpEngine,
    UdpTransportTarget,
    get_cmd,
    walk_cmd,
)

from snmp.oids import (
    PRINTER_OIDS,
    PRINTER_STATUS_MAP,
    SUPPLY_CURRENT_LEVEL_BASE,
    SUPPLY_DESCRIPTION_BASE,
    SUPPLY_MAX_CAPACITY_BASE,
    SYSTEM_OIDS,
    VENDOR_SERIAL_OIDS,
)


@dataclass
class SnmpRequestResult:
    success: bool
    value: str | None = None
    error: str | None = None


class PrinterIntelligenceEngine:
    def __init__(
        self,
        community: str = "public",
        timeout: float = 1.0,
        retries: int = 1,
    ) -> None:
        self.community = community
        self.timeout = timeout
        self.retries = retries

    async def get_value(
        self,
        ip_address: str,
        oid: str,
    ) -> SnmpRequestResult:
        try:
            transport = await UdpTransportTarget.create(
                (ip_address, 161),
                timeout=self.timeout,
                retries=self.retries,
            )

            with SnmpEngine() as engine:
                (
                    error_indication,
                    error_status,
                    error_index,
                    var_binds,
                ) = await get_cmd(
                    engine,
                    CommunityData(
                        self.community,
                        mpModel=1,
                    ),
                    transport,
                    ContextData(),
                    ObjectType(
                        ObjectIdentity(oid)
                    ),
                    lookupMib=False,
                )

            if error_indication:
                return SnmpRequestResult(
                    success=False,
                    error=str(error_indication),
                )

            if error_status:
                return SnmpRequestResult(
                    success=False,
                    error=(
                        f"{error_status.prettyPrint()} "
                        f"índice {error_index}"
                    ),
                )

            if not var_binds:
                return SnmpRequestResult(
                    success=False,
                    error="OID sem resposta.",
                )

            value = var_binds[0][1]

            if value is None:
                return SnmpRequestResult(
                    success=False,
                    error="Valor vazio.",
                )

            normalized = value.prettyPrint().strip()

            if normalized.lower() in {
                "",
                "no such object currently exists at this oid",
                "no such instance currently exists at this oid",
            }:
                return SnmpRequestResult(
                    success=False,
                    error="OID não suportado.",
                )

            return SnmpRequestResult(
                success=True,
                value=normalized,
            )

        except Exception as error:
            return SnmpRequestResult(
                success=False,
                error=str(error),
            )

    async def walk_values(
        self,
        ip_address: str,
        base_oid: str,
        maximum_rows: int = 100,
    ) -> dict[str, str]:
        values: dict[str, str] = {}

        try:
            transport = await UdpTransportTarget.create(
                (ip_address, 161),
                timeout=self.timeout,
                retries=self.retries,
            )

            with SnmpEngine() as engine:
                row_count = 0

                async for (
                    error_indication,
                    error_status,
                    error_index,
                    var_binds,
                ) in walk_cmd(
                    engine,
                    CommunityData(
                        self.community,
                        mpModel=1,
                    ),
                    transport,
                    ContextData(),
                    ObjectType(
                        ObjectIdentity(base_oid)
                    ),
                    lexicographicMode=False,
                    lookupMib=False,
                ):
                    if error_indication or error_status:
                        break

                    for oid_object, value_object in var_binds:
                        oid = oid_object.prettyPrint()
                        value = value_object.prettyPrint().strip()

                        values[oid] = value
                        row_count += 1

                        if row_count >= maximum_rows:
                            return values

            return values

        except Exception:
            return values

    async def collect(
        self,
        ip_address: str,
    ) -> dict[str, Any]:
        raw_data: dict[str, str | None] = {}
        errors: dict[str, str] = {}

        all_oids = {
            **SYSTEM_OIDS,
            **PRINTER_OIDS,
        }

        tasks = {
            field: asyncio.create_task(
                self.get_value(
                    ip_address=ip_address,
                    oid=oid,
                )
            )
            for field, oid in all_oids.items()
        }

        for field, task in tasks.items():
            result = await task

            raw_data[field] = result.value

            if result.error:
                errors[field] = result.error

        description = raw_data.get("descricao") or ""
        device_name = (
            raw_data.get("nome_dispositivo")
            or raw_data.get("nome")
            or ""
        )

        vendor = self.detect_vendor(
            f"{description} {device_name}"
        )

        serial = raw_data.get(
            "serial_printer_mib"
        )

        if not self.is_valid_serial(serial):
            serial = await self.find_vendor_serial(
                ip_address=ip_address,
                vendor=vendor,
            )

        supplies = await self.collect_supplies(
            ip_address=ip_address
        )

        page_count = self.parse_integer(
            raw_data.get("contador_paginas")
        )

        uptime_ticks = self.parse_integer(
            raw_data.get("uptime")
        )

        status_code = str(
            raw_data.get("status_impressora")
            or ""
        ).strip()

        printer_status = PRINTER_STATUS_MAP.get(
            status_code,
            "online",
        )

        model = self.detect_model(
            description=description,
            device_name=device_name,
            vendor=vendor,
        )

        toner_percentages = [
            supply["percentage"]
            for supply in supplies
            if (
                supply.get("percentage") is not None
                and self.is_toner_supply(
                    supply.get("description", "")
                )
            )
        ]

        lowest_toner = (
            min(toner_percentages)
            if toner_percentages
            else None
        )

        health_score, health_reasons = (
            self.calculate_health_score(
                snmp_online=True,
                toner_percentage=lowest_toner,
                printer_status=printer_status,
                page_count=page_count,
            )
        )

        return {
            "ip_address": ip_address,
            "community": self.community,
            "snmp_online": True,
            "dados": {
                "descricao": description or None,
                "nome": raw_data.get("nome"),
                "nome_dispositivo": (
                    device_name or None
                ),
                "fabricante": vendor,
                "modelo": model,
                "serial": serial,
                "localizacao": raw_data.get(
                    "localizacao"
                ),
                "uptime": raw_data.get("uptime"),
                "uptime_seconds": (
                    int(uptime_ticks / 100)
                    if uptime_ticks is not None
                    else None
                ),
                "contador_paginas": page_count,
                "status_impressora": printer_status,
                "status_codigo": (
                    status_code or None
                ),
                "toner_percentual": lowest_toner,
                "suprimentos": supplies,
                "health_score": health_score,
                "health_status": (
                    self.health_status(
                        health_score
                    )
                ),
                "health_reasons": health_reasons,
            },
            "erros_oids": errors,
        }

    async def collect_supplies(
        self,
        ip_address: str,
    ) -> list[dict[str, Any]]:
        descriptions, maximums, levels = (
            await asyncio.gather(
                self.walk_values(
                    ip_address,
                    SUPPLY_DESCRIPTION_BASE,
                ),
                self.walk_values(
                    ip_address,
                    SUPPLY_MAX_CAPACITY_BASE,
                ),
                self.walk_values(
                    ip_address,
                    SUPPLY_CURRENT_LEVEL_BASE,
                ),
            )
        )

        indexed_descriptions = (
            self.index_walk_values(descriptions)
        )
        indexed_maximums = (
            self.index_walk_values(maximums)
        )
        indexed_levels = (
            self.index_walk_values(levels)
        )

        all_indexes = sorted(
            set(indexed_descriptions)
            | set(indexed_maximums)
            | set(indexed_levels)
        )

        supplies: list[dict[str, Any]] = []

        for index in all_indexes:
            description = indexed_descriptions.get(
                index,
                f"Suprimento {index}",
            )

            maximum = self.parse_integer(
                indexed_maximums.get(index)
            )

            current = self.parse_integer(
                indexed_levels.get(index)
            )

            percentage = self.calculate_percentage(
                current=current,
                maximum=maximum,
            )

            supplies.append(
                {
                    "index": index,
                    "description": description,
                    "current_level": current,
                    "maximum_capacity": maximum,
                    "percentage": percentage,
                }
            )

        return supplies

    async def find_vendor_serial(
        self,
        ip_address: str,
        vendor: str,
    ) -> str | None:
        vendor_key = vendor.lower()

        oids = VENDOR_SERIAL_OIDS.get(
            vendor_key,
            VENDOR_SERIAL_OIDS["generic"],
        )

        for oid in oids:
            result = await self.get_value(
                ip_address=ip_address,
                oid=oid,
            )

            if (
                result.success
                and self.is_valid_serial(
                    result.value
                )
            ):
                return result.value

        return None

    @staticmethod
    def index_walk_values(
        values: dict[str, str],
    ) -> dict[str, str]:
        indexed: dict[str, str] = {}

        for oid, value in values.items():
            index = oid.split(".")[-1]
            indexed[index] = value

        return indexed

    @staticmethod
    def parse_integer(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        text = str(value).strip()

        match = re.search(
            r"-?\d+",
            text,
        )

        if not match:
            return None

        try:
            return int(match.group())
        except ValueError:
            return None

    @staticmethod
    def calculate_percentage(
        current: int | None,
        maximum: int | None,
    ) -> int | None:
        if current is None or maximum is None:
            return None

        if current < 0 or maximum <= 0:
            return None

        percentage = round(
            current * 100 / maximum
        )

        return max(
            0,
            min(percentage, 100),
        )

    @staticmethod
    def detect_vendor(
        content: str,
    ) -> str:
        normalized = content.lower()

        vendor_terms = (
            (("hewlett-packard", "hewlett packard", " hp "), "HP"),
            (("ricoh",), "Ricoh"),
            (("kyocera",), "Kyocera"),
            (("canon",), "Canon"),
            (("brother",), "Brother"),
            (("zebra",), "Zebra"),
            (("lexmark",), "Lexmark"),
            (("xerox",), "Xerox"),
            (("epson",), "Epson"),
            (("samsung",), "Samsung"),
        )

        padded = f" {normalized} "

        for terms, vendor in vendor_terms:
            if any(
                term in padded
                for term in terms
            ):
                return vendor

        return "Desconhecido"

    @staticmethod
    def detect_model(
        description: str,
        device_name: str,
        vendor: str,
    ) -> str | None:
        candidates = (
            device_name.strip(),
            description.strip(),
        )

        for candidate in candidates:
            if not candidate:
                continue

            if candidate.lower() in {
                vendor.lower(),
                "printer",
                "impressora",
            }:
                continue

            return candidate[:150]

        return None

    @staticmethod
    def is_valid_serial(
        value: Any,
    ) -> bool:
        if value is None:
            return False

        normalized = str(value).strip()

        if len(normalized) < 3:
            return False

        invalid_values = {
            "unknown",
            "none",
            "n/a",
            "na",
            "0",
            "-1",
        }

        return normalized.lower() not in invalid_values

    @staticmethod
    def is_toner_supply(
        description: str,
    ) -> bool:
        normalized = description.lower()

        terms = (
            "toner",
            "black",
            "cyan",
            "magenta",
            "yellow",
            "preto",
            "ciano",
            "amarelo",
        )

        return any(
            term in normalized
            for term in terms
        )

    @staticmethod
    def calculate_health_score(
        snmp_online: bool,
        toner_percentage: int | None,
        printer_status: str,
        page_count: int | None,
    ) -> tuple[int, list[str]]:
        score = 100
        reasons: list[str] = []

        if not snmp_online:
            score -= 50
            reasons.append(
                "Impressora sem resposta SNMP."
            )

        if toner_percentage is not None:
            if toner_percentage <= 5:
                score -= 30
                reasons.append(
                    "Toner em nível crítico."
                )
            elif toner_percentage <= 15:
                score -= 20
                reasons.append(
                    "Toner em nível baixo."
                )
            elif toner_percentage <= 30:
                score -= 10
                reasons.append(
                    "Toner requer acompanhamento."
                )

        if printer_status in {
            "unknown",
            "other",
        }:
            score -= 10
            reasons.append(
                "Status da impressora indefinido."
            )

        if (
            page_count is not None
            and page_count >= 500_000
        ):
            score -= 10
            reasons.append(
                "Contador elevado; avaliar manutenção."
            )

        if not reasons:
            reasons.append(
                "Nenhum risco crítico identificado."
            )

        return max(score, 0), reasons

    @staticmethod
    def health_status(
        score: int,
    ) -> str:
        if score >= 85:
            return "excellent"

        if score >= 70:
            return "good"

        if score >= 50:
            return "attention"

        return "critical"


async def collect_printer_intelligence(
    ip_address: str,
    community: str = "public",
    timeout: float = 1.0,
    retries: int = 1,
) -> dict[str, Any]:
    engine = PrinterIntelligenceEngine(
        community=community,
        timeout=timeout,
        retries=retries,
    )

    description_test = await engine.get_value(
        ip_address=ip_address,
        oid=SYSTEM_OIDS["descricao"],
    )

    if not description_test.success:
        return {
            "ip_address": ip_address,
            "community": community,
            "snmp_online": False,
            "dados": {
                "descricao": None,
                "fabricante": None,
                "modelo": None,
                "serial": None,
                "contador_paginas": None,
                "toner_percentual": None,
                "suprimentos": [],
                "health_score": 40,
                "health_status": "critical",
                "health_reasons": [
                    "Impressora sem resposta SNMP."
                ],
            },
            "erro": description_test.error,
        }

    return await engine.collect(
        ip_address=ip_address
    )
