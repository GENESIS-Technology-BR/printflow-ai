# TALVOA — SupriTech partner onboarding (controlled UAT)

## Verified 2026-10-14

- Production Supabase project: `glnmlfwtuqqngfiqsqow`.
- Production `companies_v2`: Guerra Implementos, `id=1`, active.
- Production partner tables `partners` and `partner_memberships` are **not deployed**.
- Partner portfolio code is in feature branch / draft PR #69, **not released**.

## Release gate (do not bypass)

1. CI green and staging deployment with isolated database; verify migrations and backup/restore.
2. Create staging partner `SupriTech`; assign staging copy of Guerra Implementos, never production tenant at this stage.
3. Sign in as TALVOA platform administrator. Verify `/api/v1/partners/me`, `/my-companies`, `/portfolio-summary`, and Guerra `/overview`, `/printers`, `/alerts`.
4. Validate company/Agent/printer counts, printer exclusions, counters and billing against a controlled snapshot; no production secrets or tokens copied into staging.
5. Verify partner viewer cannot mutate portal; another partner cannot read Guerra; customer portal remains disabled.
6. Obtain explicit approval before production schema migration, partner assignment, or deploy. Take verified backup and prepare rollback.

## Intended onboarding order

- Create partner SupriTech (platform admin only).
- Associate Guerra to SupriTech once (only if company unassigned); portal disabled.
- Preview portfolio using platform admin login; note this shows *all* companies, so it is **not** a substitute for real partner-scoped login testing.
- Create SupriTech partner-admin user and membership; test actual partner isolation before release.

## Safety

No production data or Agent configuration should be modified by this checklist. Do not enable customer portal implicitly.
