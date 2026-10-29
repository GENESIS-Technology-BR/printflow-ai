# TALVOA — Homologation portability readiness

This branch is for preparation only. No production deployment, database migration, or secret changes are authorized.

## Existing architecture
- Python FastAPI / Uvicorn API with SQLAlchemy and PostgreSQL (psycopg2).
- Node.js homologation gateway serves frontend/dist and proxies /api requests.
- Static React frontend is independently deployable.
- Windows Agent performs printer discovery on the customer's LAN.

## Confirmed migration blockers
1. `homolog-gateway.mjs` hardcodes the Render API origin. Replace with an environment-configured HTTPS upstream; retain host allowlisting, authorization/cookie semantics and avoid logging secrets.
2. `backend/main.py` executes schema creation and data migrations at startup for databases other than the exact name `talvoa_supritech_homolog_db`. Replace this name-based exception with an explicit, safe migration workflow before moving the API. Do not execute migrations during readiness checks.
3. FastAPI, SQLAlchemy, psycopg2, reportlab and pillow are not a drop-in Cloudflare Workers JavaScript deployment. Validate runtime compatibility and workload before selecting a provider.
4. Render SupriTech API and gateway are suspended for billing; static frontend is not suspended. Their auto-deploy settings are off.

## Read-only preflight acceptance criteria
- Document a provider that allows signup without a payment card, including any current verification requirements and free quota.
- Confirm Python runtime, persistent outbound PostgreSQL TLS connectivity, process lifecycle, CPU/memory, egress, and scheduled work support.
- Verify CORS, trusted hosts, session cookies, CSRF, scoped integration keys, and per-tenant access with automated tests.
- Ensure health endpoints distinguish liveness from database readiness; never mask API failures with gateway-only health.
- Ensure Agent offline queue replays idempotently after outages without duplicate meter readings.
- Confirm that staging uses separate secrets and database and that no production data is copied.
- Perform staging smoke tests for login, partner isolation, printer ingestion, reports and offline replay.
- Record rollback procedure and zero-cost quota alerts before enabling any deployment.

## Safe rollout
1. Audit current routes, startup lifecycle, secrets references, gateway proxy behavior, and tests.
2. Implement changes only in this isolated branch with unit tests.
3. Require CI success and review before merging.
4. Create an isolated staging environment only after the provider and account are explicitly approved.
5. Never alter production, billing, databases, deploys, or credentials as part of this preparation.
