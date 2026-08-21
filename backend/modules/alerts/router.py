from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.modules.alerts.service import reconcile_company_alerts, serialize_alert
from backend.modules.auth.dependencies import get_current_user
from backend.modules.auth.model import User
from backend.modules.dashboard.router import serialize_printer


router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts"])


@router.get("")
def list_alerts(
    status: str = Query(default="open", pattern="^(open|resolved|all)$"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    alerts = reconcile_company_alerts(db, current_user.company_id, serialize_printer)
    if status != "all":
        alerts = [alert for alert in alerts if alert.status == status]
    return [serialize_alert(alert) for alert in alerts[:limit]]
