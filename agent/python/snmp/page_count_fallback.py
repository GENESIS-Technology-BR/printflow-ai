from __future__ import annotations

from typing import Any, Awaitable, Callable


PRT_MARKER_LIFE_COUNT_BASE = "1.3.6.1.2.1.43.10.2.1.4"


def install_page_count_fallback() -> None:
    """Instala fallback para impressoras cujo contador nao esta no indice .1.1.

    Alguns equipamentos implementam prtMarkerLifeCount em outro indice da
    tabela Printer-MIB. O motor historicamente consulta somente .1.1; quando
    esse valor nao existe, fazemos um WALK apenas na coluna de life-count e
    usamos o maior contador positivo encontrado. Valores ja resolvidos pelo
    motor original nunca sao alterados.
    """
    from snmp.engine import PrinterIntelligenceEngine

    if getattr(PrinterIntelligenceEngine, "_printflow_page_count_fallback", False):
        return

    original: Callable[..., Awaitable[tuple[int | None, str, dict[str, int]]]] = (
        PrinterIntelligenceEngine.resolve_page_count
    )

    async def resolve_page_count_with_fallback(
        self: Any,
        ip_address: str,
        vendor: str,
        raw_data: dict[str, Any],
    ) -> tuple[int | None, str, dict[str, int]]:
        page_count, source, candidates = await original(
            self,
            ip_address=ip_address,
            vendor=vendor,
            raw_data=raw_data,
        )

        if page_count is not None:
            return page_count, source, candidates

        walked = await self.walk_values(
            ip_address=ip_address,
            base_oid=PRT_MARKER_LIFE_COUNT_BASE,
            maximum_rows=32,
        )

        walk_candidates: dict[str, int] = {}
        for oid, raw_value in walked.items():
            value = self.parse_integer(raw_value)
            if value is None or value <= 0:
                continue
            walk_candidates[oid] = value

        if not walk_candidates:
            return page_count, source, candidates

        # prtMarkerLifeCount pode ter mais de um indice (ex.: motores/markers).
        # Para inventario, o maior life-count positivo e o fallback mais seguro
        # para representar o contador acumulado sem somar contadores distintos.
        selected_oid, selected_value = max(
            walk_candidates.items(),
            key=lambda item: item[1],
        )

        merged_candidates = dict(candidates)
        merged_candidates.update(walk_candidates)
        merged_candidates["selected:" + selected_oid] = selected_value

        return (
            selected_value,
            "printer-mib-walk-fallback",
            merged_candidates,
        )

    PrinterIntelligenceEngine.resolve_page_count = resolve_page_count_with_fallback
    PrinterIntelligenceEngine._printflow_page_count_fallback = True
