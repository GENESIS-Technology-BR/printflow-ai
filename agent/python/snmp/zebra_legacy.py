from __future__ import annotations

import asyncio
import re
import socket
from dataclasses import dataclass


@dataclass
class ZebraLegacyResult:
    success: bool
    model: str | None = None
    firmware: str | None = None
    unique_id: str | None = None
    error: str | None = None


def _tcp_query(
    ip_address: str,
    command: bytes,
    timeout: float = 2.0,
) -> bytes:

    with socket.create_connection(
        (ip_address, 9100),
        timeout=timeout,
    ) as sock:

        sock.settimeout(timeout)
        sock.sendall(command)

        chunks: list[bytes] = []

        while True:
            try:
                chunk = sock.recv(4096)

                if not chunk:
                    break

                chunks.append(chunk)

                if len(chunk) < 4096:
                    break

            except socket.timeout:
                break

        return b"".join(chunks)


def _clean_response(data: bytes) -> str:

    text = data.decode(
        "latin-1",
        errors="replace",
    )

    text = text.replace("\x02", "")
    text = text.replace("\x03", "")
    text = text.replace("\r", "")
    text = text.replace("\n", "")

    return text.strip()


def _collect_sync(
    ip_address: str,
    timeout: float,
) -> ZebraLegacyResult:

    try:
        hi_raw = _tcp_query(
            ip_address,
            b"~HI",
            timeout,
        )

        hi = _clean_response(hi_raw)

        if not hi:
            return ZebraLegacyResult(
                success=False,
                error="Zebra porta 9100 sem resposta.",
            )

        parts = [
            item.strip()
            for item in hi.split(",")
        ]

        model = (
            parts[0]
            if parts
            else None
        )

        firmware = (
            parts[1]
            if len(parts) > 1
            else None
        )

        unique_raw = _tcp_query(
            ip_address,
            b'! U1 getvar "device.unique_id"\r\n',
            timeout,
        )

        unique_text = _clean_response(
            unique_raw
        )

        unique_id = None

        match = re.search(
            r'"([^"]+)"',
            unique_text,
        )

        if match:
            candidate = match.group(1).strip()

            if candidate and candidate != "?":
                unique_id = candidate

        return ZebraLegacyResult(
            success=True,
            model=model,
            firmware=firmware,
            unique_id=unique_id,
        )

    except Exception as exc:
        return ZebraLegacyResult(
            success=False,
            error=f"{type(exc).__name__}: {exc}",
        )


async def collect_zebra_legacy(
    ip_address: str,
    timeout: float = 2.0,
) -> ZebraLegacyResult:

    return await asyncio.to_thread(
        _collect_sync,
        ip_address,
        timeout,
    )
