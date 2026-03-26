from datetime import datetime, timezone
from typing import Optional

from app.db import SessionLocal, AuditRecord, KnowledgeContent


# ---------------------------------------------------------------------------
# Tool approval audit (existing)
# ---------------------------------------------------------------------------

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
    """Write one tool-approval audit record."""
    # Only record changes if user actually modified the args
    actual_changes = user_edited_args if user_edited_args and user_edited_args != ai_suggested_args else None
    with SessionLocal() as db:
        record = AuditRecord(
            username=username,
            action=tool_name,
            details=ai_suggested_args,
            changes=actual_changes,
            status=result_status,
            session_id=session_id,
            thread_id=thread_id,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()


def get_audit_records(
    *,
    username: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    with SessionLocal() as db:
        q = db.query(AuditRecord)
        if username:
            q = q.filter(AuditRecord.username.ilike(f"%{username}%"))
        if action:
            q = q.filter(AuditRecord.action.ilike(f"%{action}%"))
        if date_from:
            q = q.filter(AuditRecord.timestamp >= date_from)
        if date_to:
            q = q.filter(AuditRecord.timestamp <= date_to)
        rows = q.order_by(AuditRecord.timestamp.desc()).offset(offset).limit(limit).all()
        return [
            {
                "id": r.id,
                "username": r.username,
                "action": r.action,
                "details": r.details,
                "changes": r.changes,
                "status": r.status,
                "session_id": r.session_id,
                "thread_id": r.thread_id,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in rows
        ]


# ---------------------------------------------------------------------------
# Knowledge audit
# ---------------------------------------------------------------------------

def log_knowledge_action(
    *,
    username: str,
    action: str,
    doc_id: str,
    title: str,
    source_type: str,
    chunk_count: int,
    created_at: str,
    content: str,
) -> None:
    """Log knowledge.add or knowledge.delete and store full content snapshot."""
    with SessionLocal() as db:
        # Upsert content snapshot (on add: insert; on delete: content already there)
        existing = db.query(KnowledgeContent).filter(KnowledgeContent.doc_id == doc_id).first()
        if not existing:
            db.add(KnowledgeContent(
                doc_id=doc_id,
                title=title,
                source_type=source_type,
                content=content,
                created_at=created_at,
            ))

        record = AuditRecord(
            username=username,
            action=action,
            details={
                "doc_id": doc_id,
                "title": title,
                "source_type": source_type,
                "chunk_count": chunk_count,
                "created_at": created_at,
            },
            changes=None,
            status="completed",
            session_id="",
            thread_id="",
            timestamp=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()


def get_knowledge_content(doc_id: str) -> Optional[dict]:
    """Fetch full content snapshot for a document."""
    with SessionLocal() as db:
        row = db.query(KnowledgeContent).filter(KnowledgeContent.doc_id == doc_id).first()
        if not row:
            return None
        return {
            "doc_id": row.doc_id,
            "title": row.title,
            "source_type": row.source_type,
            "content": row.content,
            "created_at": row.created_at,
        }
