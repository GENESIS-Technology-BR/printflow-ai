from backend.modules.usage.router import _report_scope_label


def test_report_scope_isolates_selected_filters() -> None:
    rows = [
        {
            "printer_uuid": "printer-a",
            "display_name": "Financeiro · HP 432",
        },
        {
            "printer_uuid": "printer-b",
            "display_name": "RH · Ricoh 320F",
        },
    ]

    scope = _report_scope_label(
        rows,
        printer_uuid="printer-a",
        unit_name="Matriz",
        sector_name="Financeiro",
    )

    assert scope == (
        "Unidade: Matriz · Setor: Financeiro · "
        "Impressora: Financeiro · HP 432"
    )
    assert "RH · Ricoh 320F" not in scope


def test_report_scope_defaults_to_full_fleet() -> None:
    assert _report_scope_label([]) == "Parque completo"


def test_label_printer_detection_includes_custom_name() -> None:
    from types import SimpleNamespace
    from backend.modules.usage.router import _is_label_printer

    printer = SimpleNamespace(
        manufacturer=None, model=None, name="Generic Printer",
        custom_name="ZEBRA EXPEDICAO",
    )
    assert _is_label_printer(printer) is True
