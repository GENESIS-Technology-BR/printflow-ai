"""Health endpoint checks without starting FastAPI lifespan or touching a database."""
from unittest.mock import patch

from backend.app.routers.health import liveness, readiness


def test_liveness_does_not_connect_to_database():
    with patch("backend.app.routers.health.engine.connect", side_effect=AssertionError("unexpected database access")):
        response = liveness()
    assert response["status"] == "alive"


def test_readiness_handles_unavailable_database():
    with patch("backend.app.routers.health.engine.connect", side_effect=RuntimeError("database unavailable")):
        response = readiness()
    assert response.status_code == 503
