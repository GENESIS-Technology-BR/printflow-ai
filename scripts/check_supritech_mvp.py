"""Read-only smoke test for the isolated SupriTech MVP demo.

Usage:
  TALVOA_BASE_URL=http://127.0.0.1:8001 TALVOA_LOGIN=supritech_demo \
  TALVOA_PASSWORD='...' python -m scripts.check_supritech_mvp

Never creates accounts, changes database records, or contacts production by default.
"""
import os
import sys
from urllib.parse import urlparse

import requests


def main():
    base = os.environ.get("TALVOA_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
    parsed = urlparse(base)
    if parsed.scheme != "http" or parsed.hostname not in ("127.0.0.1", "localhost"):
        raise SystemExit("BLOQUEADO: somente API local HTTP; nao consultar ambientes remotos")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise SystemExit("BLOQUEADO: URL base invalida")
    user = os.environ.get("TALVOA_LOGIN")
    password = os.environ.get("TALVOA_PASSWORD")
    if not user or not password:
        raise SystemExit("Defina TALVOA_LOGIN e TALVOA_PASSWORD no ambiente; nao coloque senha no codigo")

    with requests.Session() as session:
        live = session.get(base + "/health/live", timeout=10)
        print("API:", live.status_code)
        live.raise_for_status()
        auth = session.post(
            base + "/api/v1/auth/login",
            json={"email": user, "password": password},
            timeout=15,
        )
        print("LOGIN:", auth.status_code)
        auth.raise_for_status()
        me = session.get(base + "/api/v1/partners/me", timeout=15)
        print("PARCEIRO:", me.status_code)
        me.raise_for_status()
        companies = session.get(base + "/api/v1/partners/my-companies", timeout=15)
        print("EMPRESAS:", companies.status_code)
        companies.raise_for_status()
        rows = companies.json()
        if not isinstance(rows, list):
            raise SystemExit("FALHA: formato inesperado de empresas")
        print("EMPRESAS VINCULADAS:", len(rows))
        for company in rows:
            company_id = company.get("id")
            if not isinstance(company_id, int):
                raise SystemExit("FALHA: ID de empresa invalido")
            result = session.get(
                f"{base}/api/v1/partners/companies/{company_id}/printers",
                timeout=15,
            )
            print(f"EMPRESA {company_id} / IMPRESSORAS:", result.status_code)
            result.raise_for_status()
            printers = result.json()
            if not isinstance(printers, list):
                raise SystemExit("FALHA: formato inesperado de impressoras")
            simulated = sum(p.get("source") == "demo" for p in printers)
            print(f"  TOTAL: {len(printers)} | MARCADAS DEMO: {simulated}")
            for printer in printers:
                print(" ", printer.get("name"), "|", printer.get("ip"), "|", printer.get("status"))
        print("SMOKE TEST: APROVADO (somente API; Agent Windows e portal web nao testados)")


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, ValueError) as exc:
        print("SMOKE TEST: FALHOU:", type(exc).__name__, file=sys.stderr)
        raise SystemExit(1) from exc
