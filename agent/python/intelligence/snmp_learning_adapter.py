from __future__ import annotations

from typing import Any, Callable, Awaitable


def build_engine_getter_factory(
    engine: Any,
) -> Callable[
    [str],
    Callable[
        [str],
        Awaitable[Any],
    ],
]:
    """
    Adapta PrinterIntelligenceEngine.get_value()
    ao Learning Mode sem duplicar o motor SNMP.
    """

    def factory(
        ip_address: str,
    ):
        async def getter(
            oid: str,
        ) -> Any:
            result = await engine.get_value(
                ip_address=ip_address,
                oid=oid,
            )

            if not getattr(
                result,
                "success",
                False,
            ):
                return None

            return getattr(
                result,
                "value",
                None,
            )

        return getter

    return factory
