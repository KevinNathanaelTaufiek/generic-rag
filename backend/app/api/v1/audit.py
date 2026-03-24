from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from app.services.audit import get_audit_records

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit(
    username: Optional[str] = Query(None),
    tool_name: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    records = get_audit_records(
        username=username,
        tool_name=tool_name,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {"records": records, "count": len(records)}
