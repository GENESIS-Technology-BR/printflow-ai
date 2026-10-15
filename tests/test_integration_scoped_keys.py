"""Security regression tests for scoped integration keys (no production access)."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.modules.integration.router import require_integration_key


def request_for(company_uuid=None):
    return SimpleNamespace(path_params={} if company_uuid is None else {"company_uuid": company_uuid}, state=SimpleNamespace())


@pytest.mark.parametrize("requested,expected_status", [("tenant-a", None), ("tenant-b", 403)])
def test_scoped_key_restricts_tenant(monkeypatch, requested, expected_status):
    monkeypatch.setenv("TALVOA_INTEGRATION_SCOPED_KEYS", json.dumps([
        {"company_uuid": "tenant-a", "key": "a" * 40},
        {"company_uuid": "tenant-b", "key": "b" * 40},
    ]))
    req = request_for(requested)
    if expected_status:
        with pytest.raises(HTTPException) as exc:
            require_integration_key(req, MagicMock(), x_talvoa_integration_key="a" * 40)
        assert exc.value.status_code == expected_status
    else:
        require_integration_key(req, MagicMock(), x_talvoa_integration_key="a" * 40)
        assert req.state.integration_company_uuids == frozenset({"tenant-a"})


def test_scoped_key_invalid_is_rejected(monkeypatch):
    monkeypatch.setenv("TALVOA_INTEGRATION_SCOPED_KEYS", json.dumps([
        {"company_uuid": "tenant-a", "key": "a" * 40},
    ]))
    with pytest.raises(HTTPException) as exc:
        require_integration_key(request_for("tenant-a"), MagicMock(), x_talvoa_integration_key="z" * 40)
    assert exc.value.status_code == 401


def test_malformed_scoped_config_fails_closed(monkeypatch):
    monkeypatch.setenv("TALVOA_INTEGRATION_SCOPED_KEYS", "{invalid")
    with pytest.raises(HTTPException) as exc:
        require_integration_key(request_for("tenant-a"), MagicMock(), x_talvoa_integration_key="a" * 40)
    assert exc.value.status_code == 503


def test_legacy_key_cannot_access_partner_tenant(monkeypatch):
    monkeypatch.delenv("TALVOA_INTEGRATION_SCOPED_KEYS", raising=False)
    monkeypatch.setenv("TALVOA_INTEGRATION_KEY", "legacy" * 8)
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(partner_id=10)
    with pytest.raises(HTTPException) as exc:
        require_integration_key(request_for("tenant-a"), db, x_talvoa_integration_key="legacy" * 8)
    assert exc.value.status_code == 403
