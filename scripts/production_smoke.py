#!/usr/bin/env python3
"""PRINTFLOW production smoke test.

Checks public production endpoints after a deploy without requiring credentials.
Exits non-zero on any contract, security-header, or availability failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class HttpResult:
    status: int
    headers: dict[str, str]
    payload: dict[str, Any]


def _request_json(url: str, timeout: float = 20.0) -> HttpResult:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "PRINTFLOW-RC1-Smoke/1.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
            payload = json.loads(body)
            return HttpResult(
                status=response.status,
                headers={k.lower(): v for k, v in response.headers.items()},
                payload=payload,
            )
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        return HttpResult(
            status=exc.code,
            headers={k.lower(): v for k, v in exc.headers.items()},
            payload=payload,
        )
    except URLError as exc:
        raise RuntimeError(f"Falha de conexão em {url}: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Resposta não JSON em {url}") from exc


def validate_health(result: HttpResult) -> None:
    if result.status != 200:
        raise AssertionError(f"/health retornou HTTP {result.status}")

    payload = result.payload
    if payload.get("status") != "healthy":
        raise AssertionError("/health não reportou status=healthy")
    if not payload.get("application"):
        raise AssertionError("/health não informou application")
    if not payload.get("version"):
        raise AssertionError("/health não informou version")
    if payload.get("environment") != "production":
        raise AssertionError("/health não está reportando environment=production")
    if not payload.get("timestamp"):
        raise AssertionError("/health não informou timestamp")


def validate_root(result: HttpResult) -> None:
    if result.status != 200:
        raise AssertionError(f"/ retornou HTTP {result.status}")

    payload = result.payload
    if payload.get("status") != "online":
        raise AssertionError("/ não reportou status=online")
    if not payload.get("application") or not payload.get("version"):
        raise AssertionError("/ não informou application/version")

    required_headers = {
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
    }
    for header, expected in required_headers.items():
        actual = result.headers.get(header)
        if actual != expected:
            raise AssertionError(
                f"Cabeçalho {header} inválido: esperado={expected!r} atual={actual!r}"
            )

    if "strict-transport-security" not in result.headers:
        raise AssertionError("HSTS ausente em produção")
    if "content-security-policy" not in result.headers:
        raise AssertionError("Content-Security-Policy ausente")


def validate_protected_routes(base_url: str) -> None:
    """Prova que rotas privadas nao aceitam acesso anonimo em producao."""
    for path in ("/api/v1/auth/me", "/api/v1/dashboard/summary"):
        result = _request_json(f"{base_url}{path}")
        if result.status not in {401, 403}:
            raise AssertionError(
                f"{path} deveria negar acesso anonimo; HTTP atual={result.status}"
            )


def run(base_url: str, attempts: int, delay_seconds: float) -> None:
    base_url = base_url.rstrip("/")
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            print(f"[PRINTFLOW] Smoke attempt {attempt}/{attempts}: {base_url}")
            health = _request_json(f"{base_url}/health")
            validate_health(health)
            root = _request_json(f"{base_url}/")
            validate_root(root)
            validate_protected_routes(base_url)
            print(
                "[PRINTFLOW] PASS "
                f"version={health.payload.get('version')} "
                f"environment={health.payload.get('environment')}"
            )
            return
        except (AssertionError, RuntimeError) as exc:
            last_error = exc
            print(f"[PRINTFLOW] Attempt {attempt} failed: {exc}", file=sys.stderr)
            if attempt < attempts:
                time.sleep(delay_seconds)

    raise SystemExit(f"[PRINTFLOW] FAIL: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PRINTFLOW RC1 production smoke test")
    parser.add_argument("base_url", help="Production API base URL, e.g. https://api.example.com")
    parser.add_argument("--attempts", type=int, default=6)
    parser.add_argument("--delay", type=float, default=20.0)
    args = parser.parse_args()

    if not args.base_url.startswith("https://"):
        raise SystemExit("Production smoke test requires an https:// URL")
    if args.attempts < 1:
        raise SystemExit("--attempts must be >= 1")

    run(args.base_url, args.attempts, args.delay)


if __name__ == "__main__":
    main()
