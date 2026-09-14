from __future__ import annotations

from typing import Any, Awaitable, Callable


PRT_MARKER_LIFE_COUNT_BASE = "1.3.6.1.2.1.43.10.2.1.4"


def install_page_count_fallback() -> None:
    """Valida o contador principal usando a coluna prtMarkerLifeCount.

    Alguns equipamentos implementam o contador fisico em outro indice da
    Printer-MIB. O motor historicamente consulta primeiro .1.1; esse indice
    pode nao existir ou pode representar apenas um marcador parcial.

    Regras desta camada:
    - contadores especificos de fabricante ja validados sao preservados;
    - para fontes Printer-MIB, fazemos WALK da coluna life-count;
    - selecionamos o maior contador positivo encontrado;
    - nunca reduzimos um contador ja obtido pelo motor original.
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

        # Fontes especificas de fabricante ja passaram por regra dedicada.
        # Nao devemos substitui-las por uma heuristica generica.
        source_normalized = str(source or "").strip().lower()
        if source_normalized not in {
            "printer-mib",
            "printer-mib-fallback",
            "printer-mib-walk-fallback",
        }:
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

        # prtMarkerLifeCount pode expor mais de um marcador. Para inventario,
        # o maior valor acumulado e o melhor representante do contador fisico.
        selected_oid, selected_value = max(
            walk_candidates.items(),
            key=lambda item: item[1],
        )

        merged_candidates = dict(candidates)
        merged_candidates.update(walk_candidates)
        merged_candidates["selected:" + selected_oid] = selected_value

        # Nunca troca um contador existente por um valor menor. Isso evita que
        # um subcontador parcial derrube um total ja conhecido.
        if page_count is not None and page_count >= selected_value:
            merged_candidates["selected:original"] = page_count
            return page_count, source, merged_candidates

        return (
            selected_value,
            "printer-mib-walk-validated",
            merged_candidates,
        )

    PrinterIntelligenceEngine.resolve_page_count = resolve_page_count_with_fallback
    PrinterIntelligenceEngine._printflow_page_count_fallback = True
