from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


SYS_DESCR = "1.3.6.1.2.1.1.1.0"
SYS_OBJECT_ID = "1.3.6.1.2.1.1.2.0"
SYS_NAME = "1.3.6.1.2.1.1.5.0"

PRINTER_SERIAL = "1.3.6.1.2.1.43.5.1.1.17.1"
PRINTER_COUNTER = "1.3.6.1.2.1.43.10.2.1.4.1.1"


@dataclass
class DeepCandidate:
    oid: str
    value: str
    candidate_type: str
    confidence: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_oid(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()

    if text.startswith("."):
        text = text[1:]

    if not re.fullmatch(r"\d+(?:\.\d+)+", text):
        return None

    return text


def enterprise_root_from_sysobjectid(
    value: Any,
) -> str | None:
    """
    Exemplo:
      1.3.6.1.4.1.10642.xxx
                ↓
      1.3.6.1.4.1.10642
    """

    oid = normalize_oid(value)

    if not oid:
        return None

    parts = oid.split(".")

    prefix = ["1", "3", "6", "1", "4", "1"]

    if parts[:6] != prefix:
        return None

    if len(parts) < 7:
        return None

    enterprise = parts[6]

    return ".".join(
        prefix + [enterprise]
    )


def normalize_value(
    value: Any,
) -> str | None:

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    invalid = {
        "none",
        "null",
        "unknown",
        "n/a",
        "na",
        "nosuchobject",
        "nosuchinstance",
        "endofmibview",
    }

    if text.lower() in invalid:
        return None

    return text


def looks_like_serial(
    value: str,
) -> tuple[bool, int, str]:

    text = value.strip()

    if len(text) < 5:
        return (
            False,
            0,
            "Muito curto.",
        )

    if len(text) > 80:
        return (
            False,
            0,
            "Muito longo.",
        )

    if (
        " " in text
        and len(text.split()) > 4
    ):
        return (
            False,
            0,
            "Parece descricao.",
        )

    has_letter = bool(
        re.search(
            r"[A-Za-z]",
            text,
        )
    )

    has_number = bool(
        re.search(
            r"\d",
            text,
        )
    )

    # --------------------------------------------------------
    # SERIAL ALFANUMERICO FORTE
    #
    # Seriais normalmente possuem mais caracteres que nomes
    # curtos de modelos como:
    #
    # ZT230
    # ZD230
    # M320F
    #
    # Valores >= 8 caracteres recebem prioridade.
    # --------------------------------------------------------

    if has_letter and has_number:

        if len(text) >= 8:
            return (
                True,
                90,
                (
                    "Valor alfanumerico longo "
                    "compativel com serial."
                ),
            )

        return (
            True,
            55,
            (
                "Alfanumerico curto; pode ser "
                "modelo ou identificador."
            ),
        )

    # --------------------------------------------------------
    # SERIAL SOMENTE NUMERICO
    # --------------------------------------------------------

    if (
        has_number
        and text.isdigit()
    ):

        if 8 <= len(text) <= 20:
            return (
                True,
                70,
                (
                    "Numero com tamanho "
                    "compativel com serial."
                ),
            )

        if 6 <= len(text) < 8:
            return (
                True,
                45,
                (
                    "Numero curto; baixa "
                    "confianca como serial."
                ),
            )

    return (
        False,
        0,
        "Baixa probabilidade de serial.",
    )

def looks_like_counter(
    value: str,
) -> tuple[bool, int, str]:

    normalized = value.replace(",", "").strip()

    if not normalized.isdigit():
        return False, 0, "Nao numerico."

    number = int(normalized)

    if number < 0:
        return False, 0, "Valor negativo."

    if number > 10_000_000_000:
        return False, 0, "Valor excessivamente alto."

    return (
        True,
        65,
        "Valor numerico compativel com contador.",
    )


def classify_walk_value(
    oid: str,
    value: Any,
) -> list[DeepCandidate]:

    text = normalize_value(value)

    if text is None:
        return []

    candidates: list[DeepCandidate] = []

    serial, serial_score, serial_reason = (
        looks_like_serial(text)
    )

    if serial:
        candidates.append(
            DeepCandidate(
                oid=oid,
                value=text,
                candidate_type="serial",
                confidence=serial_score,
                reason=serial_reason,
            )
        )

    counter, counter_score, counter_reason = (
        looks_like_counter(text)
    )

    if counter:
        candidates.append(
            DeepCandidate(
                oid=oid,
                value=text,
                candidate_type="counter",
                confidence=counter_score,
                reason=counter_reason,
            )
        )

    return candidates
