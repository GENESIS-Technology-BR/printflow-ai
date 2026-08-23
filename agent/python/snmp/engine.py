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

from intelligence.printer_v3 import build_identity, normalize_snmp_text

from snmp.zebra_legacy import collect_zebra_legacy

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



# ============================================================
# PRINTFLOW - PAGE COUNT INTELLIGENCE
# ============================================================
# Printer-MIB = fallback universal.
#
# OIDs privados somente vencem quando existe consenso entre
# pelo menos dois contadores validos.
#
# Canon GX6000 validada em equipamento real.
# ============================================================

VENDOR_PAGE_COUNT_OIDS = {
    "canon": (
        "1.3.6.1.4.1.1602.1.11.2.1.1.3.1",
        "1.3.6.1.4.1.1602.1.11.2.1.1.3.2",
        "1.3.6.1.4.1.1602.1.11.2.1.1.3.4",
    ),
    "zebra": (
        "1.3.6.1.4.1.10642.1.20.1",
    ),
}


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
                        mpModel=0,
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
                        mpModel=0,
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

        zebra_legacy = None

        if str(vendor or "").strip().lower() == "zebra":
            zebra_legacy = await collect_zebra_legacy(
                ip_address=ip_address,
                timeout=max(
                    min(self.timeout, 2.0),
                    1.0,
                ),
            )

        vendor_key = str(
            vendor or ""
        ).strip().lower()

        serial = raw_data.get(
            "serial_printer_mib"
        )

        # ZebraNet legado:
        # o sysName frequentemente e o serial fisico,
        # como ZBR2964338.
        if (
            vendor_key == "zebra"
            and not self.is_valid_serial(serial)
        ):
            zebra_sys_name = raw_data.get("nome")

            if self.is_valid_serial(
                zebra_sys_name
            ):
                serial = zebra_sys_name

        if not self.is_valid_serial(serial):
            serial = await self.find_vendor_serial(
                ip_address=ip_address,
                vendor=vendor,
            )

        supplies = await self.collect_supplies(
            ip_address=ip_address
        )

        (
            page_count,
            page_count_source,
            page_count_candidates,
        ) = await self.resolve_page_count(
            ip_address=ip_address,
            vendor=vendor,
            raw_data=raw_data,
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

        if (
            zebra_legacy is not None
            and zebra_legacy.success
        ):
            if zebra_legacy.model:
                model = zebra_legacy.model

            if (
                not self.is_valid_serial(serial)
                and zebra_legacy.unique_id
            ):
                serial = zebra_legacy.unique_id

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

        # ====================================================
        # PRINTFLOW_V3_IDENTITY
        # Normaliza fabricante/modelo/serial/nome.
        # Contador, toner e status permanecem preservados.
        # ====================================================

        identity_v3 = build_identity(
            manufacturer=vendor,
            model=model,
            serial=serial,
            description=description,
            device_name=device_name,
            hostname=raw_data.get("nome"),
            open_ports=(),
            snmp_online=True,
        )

        if identity_v3.manufacturer:
            vendor = identity_v3.manufacturer

        if identity_v3.model:
            model = identity_v3.model

        if identity_v3.serial:
            serial = identity_v3.serial

        description = (
            identity_v3.normalized_description
            or normalize_snmp_text(description)
            or description
        )

        device_name = (
            identity_v3.normalized_name
            or normalize_snmp_text(device_name)
            or device_name
        )

        display_name_v3 = identity_v3.display_name

        health_score, health_reasons = (
            self.calculate_health_score(
                snmp_online=True,
                toner_percentage=lowest_toner,
                printer_status=printer_status,
                page_count=page_count,
            )
        )

        # ====================================================
        # PRINTFLOW SAFE WALK FALLBACK B13
        #
        # Executa somente quando identidade importante estiver
        # ausente. Nunca substitui valores SNMP ja confirmados.
        # Contadores encontrados pelo Learning permanecem apenas
        # como diagnostico ate o OID ser validado.
        # ====================================================

        learning_diagnostic = None

        if (
            vendor_key != "zebra"
            and (
                not self.is_valid_serial(serial)
                or page_count is None
            )
        ):
            try:
                from intelligence.snmp_walk_executor import (
                    safe_walk_printer,
                )
                from intelligence.snmp_safe_walk import (
                    best_candidates,
                )

                walk_result = await safe_walk_printer(
                    ip_address=ip_address,
                    community=self.community,
                    timeout=min(self.timeout, 1.0),
                    retries=0,
                )

                serial_candidates = best_candidates(
                    walk_result.analysis,
                    "serial",
                    limit=5,
                )

                counter_candidates = best_candidates(
                    walk_result.analysis,
                    "counter",
                    limit=10,
                )

                # Serial: somente candidato de alta confianca.
                # Valores ja existentes nunca sao substituidos.
                if not self.is_valid_serial(serial):
                    strong_serials = [
                        candidate
                        for candidate in serial_candidates
                        if candidate.confidence >= 85
                    ]

                    if strong_serials:
                        serial = strong_serials[0].value

                learning_diagnostic = {
                    "sys_object_id": (
                        walk_result.sys_object_id
                    ),
                    "error": walk_result.error,
                    "rows_seen": (
                        walk_result.analysis.rows_seen
                    ),
                    "truncated": (
                        walk_result.analysis.truncated
                    ),
                    "serial_candidates": [
                        candidate.to_dict()
                        for candidate in serial_candidates
                    ],
                    "counter_candidates": [
                        candidate.to_dict()
                        for candidate in counter_candidates
                    ],
                }

            except Exception as exc:
                learning_diagnostic = {
                    "error": (
                        f"{type(exc).__name__}: {exc}"
                    ),
                    "serial_candidates": [],
                    "counter_candidates": [],
                }

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
            "display_name": display_name_v3,
            "identity_confidence": identity_v3.confidence_score,
            "identity_v3": identity_v3.to_dict(),
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
                "contador_origem": page_count_source,
                "contador_candidatos": page_count_candidates,
                "status_impressora": printer_status,
                "status_codigo": (
                    status_code or None
                ),
                "toner_percentual": lowest_toner,
            "learning_diagnostic": learning_diagnostic,
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

    async def resolve_page_count(
        self,
        ip_address: str,
        vendor: str,
        raw_data: dict[str, Any],
    ) -> tuple[int | None, str, dict[str, int]]:
        """
        Seleciona o contador principal da impressora.

        Prioridade:
        - contador privado confiavel do fabricante;
        - Printer-MIB como fallback universal.
        """

        parser = (
            getattr(self, "parse_integer", None)
            or getattr(self, "_parse_integer", None)
        )

        if parser is None:
            raise RuntimeError(
                "Parser de inteiros nao encontrado no motor SNMP."
            )

        generic_count = parser(
            raw_data.get("contador_paginas")
        )

        vendor_key = str(
            vendor or ""
        ).strip().lower()

        vendor_oids = VENDOR_PAGE_COUNT_OIDS.get(
            vendor_key,
            (),
        )

        candidates: dict[str, int] = {}

        if not vendor_oids:
            return (
                generic_count,
                "printer-mib",
                candidates,
            )

        results = await asyncio.gather(
            *[
                self.get_value(
                    ip_address=ip_address,
                    oid=oid,
                )
                for oid in vendor_oids
            ],
            return_exceptions=True,
        )

        for oid, result in zip(vendor_oids, results):

            if isinstance(result, Exception):
                continue

            if not getattr(result, "success", False):
                continue

            value = parser(
                getattr(result, "value", None)
            )

            if value is None or value < 0:
                continue

            candidates[oid] = value

        if not candidates:
            return (
                generic_count,
                "printer-mib-fallback",
                candidates,
            )

        frequencies: dict[int, int] = {}

        for value in candidates.values():
            frequencies[value] = (
                frequencies.get(value, 0) + 1
            )

        selected_value = None
        selected_frequency = 0

        for value, frequency in frequencies.items():

            if frequency > selected_frequency:
                selected_value = value
                selected_frequency = frequency

        # Fabricantes com multiplos OIDs exigem consenso.
        if (
            selected_value is not None
            and selected_frequency >= 2
        ):
            return (
                selected_value,
                f"{vendor_key}-vendor-consensus",
                candidates,
            )

        # Zebra legado possui contador enterprise direto.
        if (
            vendor_key == "zebra"
            and len(candidates) == 1
        ):
            zebra_value = next(
                iter(candidates.values())
            )

            return (
                zebra_value,
                "zebra-enterprise-oid",
                candidates,
            )

        return (
            generic_count,
            "printer-mib-fallback",
            candidates,
        )

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
