from __future__ import annotations


SYSTEM_OIDS = {
    "descricao": "1.3.6.1.2.1.1.1.0",
    "uptime": "1.3.6.1.2.1.1.3.0",
    "nome": "1.3.6.1.2.1.1.5.0",
    "localizacao": "1.3.6.1.2.1.1.6.0",
}


PRINTER_OIDS = {
    "contador_paginas": "1.3.6.1.2.1.43.10.2.1.4.1.1",
    "status_impressora": "1.3.6.1.2.1.25.3.5.1.1.1",
    "serial_printer_mib": "1.3.6.1.2.1.43.5.1.1.17.1",
    "nome_dispositivo": "1.3.6.1.2.1.25.3.2.1.3.1",
}


VENDOR_SERIAL_OIDS = {
    "hp": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
        "1.3.6.1.4.1.11.2.3.9.1.1.7.0",
    ),
    "ricoh": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
    ),
    "kyocera": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
    ),
    "canon": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
    ),
    "brother": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
    ),
    "zebra": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
    ),
    "generic": (
        "1.3.6.1.2.1.43.5.1.1.17.1",
    ),
}


SUPPLY_DESCRIPTION_BASE = "1.3.6.1.2.1.43.11.1.1.6"
SUPPLY_MAX_CAPACITY_BASE = "1.3.6.1.2.1.43.11.1.1.8"
SUPPLY_CURRENT_LEVEL_BASE = "1.3.6.1.2.1.43.11.1.1.9"


PRINTER_STATUS_MAP = {
    "1": "other",
    "2": "unknown",
    "3": "idle",
    "4": "printing",
    "5": "warmup",
}
