from __future__ import annotations

import socket

PRINTER_PORTS = (
    9100,
    515,
    631,
    161,
)


def is_printer(ip: str) -> bool:

    for port in PRINTER_PORTS:

        try:

            with socket.create_connection(
                (ip, port),
                timeout=0.5,
            ):
                return True

        except Exception:
            pass

    return False