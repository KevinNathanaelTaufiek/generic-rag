from datetime import datetime, timezone
from typing import Optional

from app.db import SessionLocal, ToolAuditRecord


def log_tool_approval(
    *,
    username: str,
    tool_name: str,
    ai_suggested_args: dict,
    user_edited_args: Optional[dict],
    result_status: str,
    session_id: str,
    thread_id: str,
) -> None:
    """Write one audit record synchronously."""
    with SessionLocal() as db:
        record = ToolAuditRecord(
            username=username,
            tool_name=tool_name,
            ai_suggested_args=ai_suggested_args,
            user_edited_args=user_edited_args,
            result_status=result_status,
            session_id=session_id,
            thread_id=thread_id,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()


def get_audit_records(
    *,
    username: Optional[str] = None,
    tool_name: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    with SessionLocal() as db:
        q = db.query(ToolAuditRecord)
        if username:
            q = q.filter(ToolAuditRecord.username.ilike(f"%{username}%"))
        if tool_name:
            q = q.filter(ToolAuditRecord.tool_name.ilike(f"%{tool_name}%"))
        if date_from:
            q = q.filter(ToolAuditRecord.timestamp >= date_from)
        if date_to:
            q = q.filter(ToolAuditRecord.timestamp <= date_to)
        rows = q.order_by(ToolAuditRecord.timestamp.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": r.id,
                "username": r.username,
                "tool_name": r.tool_name,
                "ai_suggested_args": r.ai_suggested_args,
                "user_edited_args": r.user_edited_args,
                "result_status": r.result_status,
                "session_id": r.session_id,
                "thread_id": r.thread_id,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ]
