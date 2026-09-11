from scripts.production_smoke import HttpResult, validate_health, validate_root


def test_validate_health_accepts_production_contract():
    validate_health(
        HttpResult(
            status=200,
            headers={},
            payload={
                "application": "PRINTFLOW",
                "version": "1.0.0",
                "environment": "production",
                "status": "healthy",
                "timestamp": "2026-09-11T10:00:00+00:00",
            },
        )
    )


def test_validate_root_accepts_security_contract():
    validate_root(
        HttpResult(
            status=200,
            headers={
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "referrer-policy": "no-referrer",
                "strict-transport-security": "max-age=31536000; includeSubDomains",
                "content-security-policy": "default-src 'none'",
            },
            payload={
                "application": "PRINTFLOW",
                "version": "1.0.0",
                "status": "online",
            },
        )
    )


def test_validate_health_rejects_non_production_environment():
    result = HttpResult(
        status=200,
        headers={},
        payload={
            "application": "PRINTFLOW",
            "version": "1.0.0",
            "environment": "development",
            "status": "healthy",
            "timestamp": "2026-09-11T10:00:00+00:00",
        },
    )

    try:
        validate_health(result)
    except AssertionError as exc:
        assert "environment=production" in str(exc)
    else:
        raise AssertionError("Smoke contract deveria rejeitar ambiente não produtivo")
