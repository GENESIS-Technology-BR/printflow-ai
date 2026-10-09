from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.alerts.service import (
    acknowledge_alert,
    reconcile_company_alerts,
    serialize_alert,
)
from backend.modules.auth.dependencies import get_current_user, get_platform_admin
from backend.modules.auth.model import User
from backend.modules.partners.access import require_legacy_company_portal_access
from backend.modules.dashboard.router import serialize_printer


router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


def get_legacy_portal_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    require_legacy_company_portal_access(db, current_user)
    return current_user



@router.get("")
def list_alerts(
    status: str = Query(
        default="open", pattern="^(open|acknowledged|resolved|all)$"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_legacy_portal_user),
):
    alerts = reconcile_company_alerts(db, current_user.company_id, serialize_printer)
    if status == "open":
        alerts = [alert for alert in alerts if alert.status in ("open", "acknowledged")]
    elif status != "all":
        alerts = [alert for alert in alerts if alert.status == status]
    return [serialize_alert(alert) for alert in alerts[:limit]]


@router.post("/{alert_id}/acknowledge")
def acknowledge_operational_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_platform_admin),
):
    alert = acknowledge_alert(
        db, current_user.company_id, alert_id, current_user.id
    )
    if alert is None:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Alerta ativo não encontrado.",
        )
    return serialize_alert(alert)
