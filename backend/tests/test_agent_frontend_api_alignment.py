from pathlib import Path


def test_frontend_default_matches_documented_agent_api():
    root = Path(__file__).resolve().parents[2]
    official_api = "https://printflow-api-3uwr.onrender.com"
    for relative_path in (
        "frontend/src/services/api.ts",
        "agent/python/config/settings.py",
        "agent/windows/Start-TALVOA-Agent.ps1",
        "docs/PRODUCTION-ARCHITECTURE.md",
    ):
        assert official_api in (root / relative_path).read_text(encoding="utf-8")
    frontend = (root / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    assert "import.meta.env.VITE_API_URL ||" in frontend
    assert '"https://printflow-api-genesis.onrender.com"' not in frontend
