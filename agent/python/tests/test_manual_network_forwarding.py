from __future__ import annotations

import inspect

from core.service import PrintflowAgentService


def test_service_forwards_manual_networks():
    source = inspect.getsource(
        PrintflowAgentService.discover_devices
    )

    assert (
        "manual_networks=self.manual_networks"
        in source
    )


def test_manual_network_is_not_hardcoded():
    source = inspect.getsource(
        PrintflowAgentService.discover_devices
    )

    assert "10.2.128.0/24" not in source
    assert "10.2.129.0/24" not in source
