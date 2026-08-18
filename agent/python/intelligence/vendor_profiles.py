from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VendorProfile:
    name: str
    serial_oids: tuple[str, ...]
    page_count_oids: tuple[str, ...]
    description_oids: tuple[str, ...]


PRINTER_MIB_SERIAL = "1.3.6.1.2.1.43.5.1.1.17.1"
PRINTER_MIB_COUNTER = "1.3.6.1.2.1.43.10.2.1.4.1.1"
SYS_DESCR = "1.3.6.1.2.1.1.1.0"

HP_SERIAL = "1.3.6.1.4.1.11.2.3.9.1.1.7.0"


GENERIC_PROFILE = VendorProfile(
    name="generic",
    serial_oids=(
        PRINTER_MIB_SERIAL,
    ),
    page_count_oids=(
        PRINTER_MIB_COUNTER,
    ),
    description_oids=(
        SYS_DESCR,
    ),
)


VENDOR_PROFILES: dict[str, VendorProfile] = {
    "hp": VendorProfile(
        name="HP",
        serial_oids=(
            PRINTER_MIB_SERIAL,
            HP_SERIAL,
        ),
        page_count_oids=(
            PRINTER_MIB_COUNTER,
        ),
        description_oids=(
            SYS_DESCR,
        ),
    ),
    "ricoh": VendorProfile(
        name="Ricoh",
        serial_oids=(
            PRINTER_MIB_SERIAL,
        ),
        page_count_oids=(
            PRINTER_MIB_COUNTER,
        ),
        description_oids=(
            SYS_DESCR,
        ),
    ),
    "kyocera": VendorProfile(
        name="Kyocera",
        serial_oids=(
            PRINTER_MIB_SERIAL,
        ),
        page_count_oids=(
            PRINTER_MIB_COUNTER,
        ),
        description_oids=(
            SYS_DESCR,
        ),
    ),
    "canon": VendorProfile(
        name="Canon",
        serial_oids=(
            PRINTER_MIB_SERIAL,
        ),
        page_count_oids=(
            PRINTER_MIB_COUNTER,
        ),
        description_oids=(
            SYS_DESCR,
        ),
    ),
    "brother": VendorProfile(
        name="Brother",
        serial_oids=(
            PRINTER_MIB_SERIAL,
        ),
        page_count_oids=(
            PRINTER_MIB_COUNTER,
        ),
        description_oids=(
            SYS_DESCR,
        ),
    ),
    "zebra": VendorProfile(
        name="Zebra",
        serial_oids=(
            PRINTER_MIB_SERIAL,
        ),
        page_count_oids=(
            PRINTER_MIB_COUNTER,
        ),
        description_oids=(
            SYS_DESCR,
        ),
    ),
}


def get_vendor_profile(vendor: str | None) -> VendorProfile:
    if not vendor:
        return GENERIC_PROFILE

    key = vendor.strip().lower()

    return VENDOR_PROFILES.get(
        key,
        GENERIC_PROFILE,
    )
