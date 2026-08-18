from intelligence.printer_v3 import (
    normalize_snmp_text,
    detect_vendor,
    build_identity,
    calculate_printer_confidence,
)

from diagnostic_robot import DiagnosticRobot


def test_hex_canon():

    raw = (
        "0x43414e4f4e204950462d373730"
        "000000000000000000000000"
    )

    decoded = normalize_snmp_text(
        raw
    )

    assert decoded is not None
    assert "CANON" in decoded.upper()
    assert "IPF-770" in decoded.upper()


def test_vendor_detection():

    assert (
        detect_vendor(
            "Canon iPF770"
        )
        == "Canon"
    )

    assert (
        detect_vendor(
            "RICOH M 320F"
        )
        == "Ricoh"
    )

    assert (
        detect_vendor(
            "HP Laser MFP 432fdn"
        )
        == "HP"
    )


def test_identity_canon():

    identity = build_identity(
        description=(
            "0x43414e4f4e204950462d373730"
            "000000000000"
        ),
        device_name=None,
        model=None,
        serial=None,
        hostname=None,
        open_ports=[
            80,
            443,
            515,
            631,
            9100,
            161,
        ],
        snmp_online=True,
    )

    assert identity.manufacturer == "Canon"

    assert identity.confidence_score >= 80

    assert "CANON" in identity.display_name.upper()


def test_confidence():

    score = calculate_printer_confidence(
        open_ports=[
            9100,
            631,
            161,
        ],
        manufacturer="Ricoh",
        model="M 320F",
        serial="ABC123",
        snmp_online=True,
    )

    assert score == 100


def test_robot_security():

    robot = DiagnosticRobot()

    result = robot.execute(
        "FORMAT_C"
    )

    assert result.success is False


def test_robot_system_info():

    robot = DiagnosticRobot()

    result = robot.execute(
        "SYSTEM_INFO"
    )

    assert result.success is True
    assert "hostname" in result.data


if __name__ == "__main__":

    tests = [
        test_hex_canon,
        test_vendor_detection,
        test_identity_canon,
        test_confidence,
        test_robot_security,
        test_robot_system_info,
    ]

    for test in tests:

        test()

        print(
            f"{test.__name__}: OK"
        )

    print()
    print(
        "TODOS OS TESTES FRENTE A V3: OK"
    )
