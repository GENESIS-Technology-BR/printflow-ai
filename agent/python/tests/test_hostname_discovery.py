import socket

from config.settings import AgentSettings
from discovery_runner import resolve_hostname


def test_reverse_dns_hostname(monkeypatch):
    monkeypatch.setattr(
        socket,
        "gethostbyaddr",
        lambda ip: (
            "PRN-FISCAL-01.empresa.local",
            [],
            [ip],
        ),
    )

    assert (
        resolve_hostname("10.2.0.101")
        == "PRN-FISCAL-01.empresa.local"
    )


def test_hostname_resolution_enabled_by_default(
    monkeypatch,
):
    monkeypatch.delenv(
        "PRINTFLOW_RESOLVE_NAMES",
        raising=False,
    )

    settings = AgentSettings.load()

    assert settings.resolve_names is True
