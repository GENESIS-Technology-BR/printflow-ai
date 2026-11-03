"""Pure, fail-closed tenant authorization policy (not wired to production API).

A service must still authenticate the actor, resolve authorized tenant scope
server-side, and audit every mutation before using this decision.
"""
from dataclasses import dataclass
from typing import FrozenSet, Optional


@dataclass(frozen=True)
class Actor:
    role: str
    company_id: Optional[str]
    authorized_tenants: FrozenSet[str] = frozenset()


def may_access_tenant(actor: Actor, target_tenant: Optional[str], *, mutate: bool) -> bool:
    """Deny missing targets, unknown roles and unauthorized cross-tenant access."""
    if not target_tenant or not target_tenant.strip():
        return False
    if actor.role == "client":
        return not mutate and actor.company_id == target_tenant
    if actor.role == "platform_admin":
        # No implicit global access: tenant must be explicitly authorized.
        return target_tenant in actor.authorized_tenants
    return False
