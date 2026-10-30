# TALVOA — MVP SupriTech: isolated homologation runbook

## Status and scope
The Render SupriTech API and gateway are suspended for billing. The static portal alone is **not** a functional demo. Do not change production, existing databases, secrets, or DNS while preparing a replacement.

## Safe startup contract
The FastAPI HTTP lifespan does not create tables, apply schema migrations, configure Guerra financial settings, or bootstrap an administrator. Apply reviewed migrations separately against a **new, dedicated staging PostgreSQL database** before starting the service. Never point an isolated demo at production.

## Minimum environment checklist
- `ENVIRONMENT=staging` (requires PostgreSQL; SQLite fallback is prohibited).
- `DATABASE_URL`: dedicated staging PostgreSQL URL supplied as a hosting secret; never commit it.
- `TALVOA_ALLOWED_HOSTS`: exact demo API hostname(s).
- `TALVOA_CORS_ORIGINS`: exact demo portal origin.
- `TALVOA_ALLOW_STAGING_BOOTSTRAP`: leave unset. Admin provisioning must be a separate, audited step.
- Review other application auth/session secrets and integration keys required by existing settings before deployment; do not invent defaults for a public demo.

## API smoke checks (no credentials in logs)
1. Deploy the tested rescue branch to a **new** staging service only after migration review.
2. `GET /health/live` must return 200 (process alive, independent of DB).
3. `GET /health/ready` must return 200 (DB round trip); 503 means do not open demo access.
4. Verify authorized partner login and denied cross-tenant requests (403); run isolation regression suite.
5. Confirm printer data is real and belongs to the correct customer. If Agent data is unavailable, explicitly label the demonstration as simulated; do not present mock values as live telemetry.
6. Generate a customer-scoped report and verify the 20–19 billing period and Guerra exclusions before using financial results.

## Go / no-go
**GO** only if API + DB + login + tenancy isolation + printers + report pass end to end. Otherwise demonstrate the UI as a prototype, with clear disclosure that integration is not yet validated.

## Rollback
Stop the isolated staging service. Do not repoint production DNS, change Render production, or restore a database without an explicit recovery plan.
