from __future__ import annotations

import re
from typing import Any


def decode_hex_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    lowered = text.lower()

    if lowered.startswith("0x"):
        hex_part = text[2:]

        if len(hex_part) % 2 != 0:
            return text

        if not re.fullmatch(r"[0-9a-fA-F]+", hex_part):
            return text

        try:
            raw = bytes.fromhex(hex_part)
        except ValueError:
            return text

        for encoding in ("utf-8", "latin-1"):
            try:
                decoded = raw.decode(encoding, errors="strict")
                decoded = decoded.replace("\x00", "").strip()

                if decoded:
                    return decoded
            except UnicodeDecodeError:
                continue

        return text

    return text


def normalize_text(value: Any) -> str | None:
    decoded = decode_hex_text(value)

    if decoded is None:
        return None

    text = decoded.replace("\x00", " ").strip()

    text = re.sub(r"\s+", " ", text)

    if not text:
        return None

    return text


def normalize_vendor(value: Any) -> str | None:
    text = normalize_text(value)

    if not text:
        return None

    normalized = text.lower()

    vendors = (
        (("hewlett-packard", "hewlett packard", "hp"), "HP"),
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

    for terms, vendor in vendors:
        for term in terms:
            if term in padded:
                return vendor

    return text[:100]
