from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any
import re


INVALID_TEXT_VALUES = {
    "",
    "unknown",
    "none",
    "null",
    "n/a",
    "na",
    "-",
    "--",
    "0",
    "-1",
}


VENDOR_ALIASES = {
    "hp": "HP",
    "hewlett packard": "HP",
    "hewlett-packard": "HP",

    "canon": "Canon",

    "ricoh": "Ricoh",

    "kyocera": "Kyocera",

    "brother": "Brother",

    "zebra": "Zebra",

    "lexmark": "Lexmark",

    "xerox": "Xerox",

    "epson": "Epson",

    "samsung": "Samsung",

    "oki": "OKI",

    "konica": "Konica Minolta",
    "minolta": "Konica Minolta",

    "sharp": "Sharp",
}


PRINTER_PORT_WEIGHTS = {
    9100: 35,  # RAW/JetDirect
    631: 25,   # IPP
    515: 20,   # LPR
    161: 30,   # SNMP
    443: 5,    # HTTPS
    80: 5,     # HTTP
}


@dataclass
class PrinterIdentity:
    manufacturer: str | None = None
    model: str | None = None
    serial: str | None = None
    display_name: str | None = None

    confidence_score: int = 0

    raw_description: str | None = None
    raw_name: str | None = None

    normalized_description: str | None = None
    normalized_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _decode_hex_string(value: str) -> str | None:
    """
    Decodifica valores SNMP que chegam como:
    0x43414e4f4e...
    """

    text = value.strip()

    if not text.lower().startswith("0x"):
        return None

    hex_data = text[2:]

    # remove caracteres que nao sejam HEX
    hex_data = re.sub(
        r"[^0-9a-fA-F]",
        "",
        hex_data,
    )

    if len(hex_data) < 2:
        return None

    # hexadecimal precisa ter quantidade par
    if len(hex_data) % 2:
        hex_data = hex_data[:-1]

    try:
        raw = bytes.fromhex(hex_data)
    except ValueError:
        return None

    # remove NULL padding comum em SNMP
    raw = raw.rstrip(b"\x00")

    if not raw:
        return None

    for encoding in (
        "utf-8",
        "latin-1",
        "cp1252",
    ):
        try:
            decoded = raw.decode(
                encoding,
                errors="strict",
            ).strip()

            if decoded:
                return decoded

        except UnicodeDecodeError:
            continue

    return None


def normalize_snmp_text(
    value: Any,
) -> str | None:
    """
    Normaliza strings vindas de SNMP.

    Corrige:
    - bytes
    - hexadecimal 0x...
    - NULL padding
    - espacos duplicados
    - valores invalidos
    """

    if value is None:
        return None

    if isinstance(value, bytes):

        raw = value.rstrip(b"\x00")

        for encoding in (
            "utf-8",
            "latin-1",
            "cp1252",
        ):
            try:
                text = raw.decode(
                    encoding,
                    errors="strict",
                )
                break

            except UnicodeDecodeError:
                text = ""

    else:
        text = str(value)

    text = text.strip()

    if not text:
        return None

    decoded_hex = _decode_hex_string(text)

    if decoded_hex:
        text = decoded_hex

    # limpa NULL textual
    text = text.replace(
        "\x00",
        "",
    )

    # remove espacos excessivos
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if text.lower() in INVALID_TEXT_VALUES:
        return None

    # rejeita string aparentemente binaria/lixo
    printable = sum(
        1
        for char in text
        if char.isprintable()
    )

    if text and printable / len(text) < 0.80:
        return None

    return text


def detect_vendor(
    *values: Any,
) -> str | None:

    combined_parts: list[str] = []

    for value in values:

        normalized = normalize_snmp_text(
            value
        )

        if normalized:
            combined_parts.append(
                normalized.lower()
            )

    combined = " ".join(
        combined_parts
    )

    if not combined:
        return None

    for alias, canonical in VENDOR_ALIASES.items():

        if alias in combined:
            return canonical

    return None


def normalize_model(
    model: Any,
    description: Any = None,
    device_name: Any = None,
    vendor: Any = None,
) -> str | None:

    candidates = (
        model,
        device_name,
        description,
    )

    vendor_norm = (
        normalize_snmp_text(vendor)
        or ""
    ).lower()

    for candidate in candidates:

        text = normalize_snmp_text(
            candidate
        )

        if not text:
            continue

        low = text.lower()

        if low in {
            "printer",
            "impressora",
            "unknown",
        }:
            continue

        if vendor_norm and low == vendor_norm:
            continue

        # corta descricoes absurdamente grandes
        return text[:180]

    return None


def normalize_serial(
    value: Any,
) -> str | None:

    serial = normalize_snmp_text(
        value
    )

    if not serial:
        return None

    if len(serial) < 3:
        return None

    if serial.lower() in INVALID_TEXT_VALUES:
        return None

    return serial[:180]


def build_display_name(
    manufacturer: Any,
    model: Any,
    hostname: Any = None,
) -> str:

    manufacturer_text = normalize_snmp_text(
        manufacturer
    )

    model_text = normalize_snmp_text(
        model
    )

    hostname_text = normalize_snmp_text(
        hostname
    )

    if manufacturer_text and model_text:

        if (
            manufacturer_text.lower()
            in model_text.lower()
        ):
            return model_text[:150]

        return (
            f"{manufacturer_text} "
            f"{model_text}"
        )[:150]

    if model_text:
        return model_text[:150]

    if hostname_text:
        return hostname_text[:150]

    if manufacturer_text:
        return manufacturer_text[:150]

    return "Impressora"


def calculate_port_score(
    open_ports: list[int] | tuple[int, ...] | set[int],
) -> int:

    score = 0

    ports = {
        int(port)
        for port in open_ports
        if str(port).isdigit()
    }

    for port, weight in PRINTER_PORT_WEIGHTS.items():

        if port in ports:
            score += weight

    return min(
        score,
        100,
    )


def calculate_printer_confidence(
    *,
    open_ports: list[int] | tuple[int, ...] | set[int] = (),
    manufacturer: Any = None,
    model: Any = None,
    serial: Any = None,
    snmp_online: bool = False,
) -> int:

    score = calculate_port_score(
        open_ports
    )

    if snmp_online:
        score += 20

    if normalize_snmp_text(
        manufacturer
    ):
        score += 10

    if normalize_snmp_text(
        model
    ):
        score += 10

    if normalize_serial(
        serial
    ):
        score += 10

    return max(
        0,
        min(score, 100),
    )


def build_identity(
    *,
    manufacturer: Any = None,
    model: Any = None,
    serial: Any = None,
    description: Any = None,
    device_name: Any = None,
    hostname: Any = None,
    open_ports: list[int] | tuple[int, ...] | set[int] = (),
    snmp_online: bool = False,
) -> PrinterIdentity:

    normalized_description = normalize_snmp_text(
        description
    )

    normalized_name = normalize_snmp_text(
        device_name
    )

    detected_vendor = (
        normalize_snmp_text(
            manufacturer
        )
        or detect_vendor(
            manufacturer,
            model,
            description,
            device_name,
            hostname,
        )
    )

    detected_model = normalize_model(
        model=model,
        description=normalized_description,
        device_name=normalized_name,
        vendor=detected_vendor,
    )

    detected_serial = normalize_serial(
        serial
    )

    display_name = build_display_name(
        manufacturer=detected_vendor,
        model=detected_model,
        hostname=hostname,
    )

    confidence = calculate_printer_confidence(
        open_ports=open_ports,
        manufacturer=detected_vendor,
        model=detected_model,
        serial=detected_serial,
        snmp_online=snmp_online,
    )

    return PrinterIdentity(
        manufacturer=detected_vendor,
        model=detected_model,
        serial=detected_serial,
        display_name=display_name,
        confidence_score=confidence,
        raw_description=(
            str(description)
            if description is not None
            else None
        ),
        raw_name=(
            str(device_name)
            if device_name is not None
            else None
        ),
        normalized_description=normalized_description,
        normalized_name=normalized_name,
    )
