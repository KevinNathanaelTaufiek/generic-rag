from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, JSON, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./data/audit.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class ToolAuditRecord(Base):
    __tablename__ = "tool_audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, index=True)
    tool_name = Column(String, nullable=False, index=True)
    ai_suggested_args = Column(JSON, nullable=False)
    user_edited_args = Column(JSON, nullable=True)   # None if user didn't edit
    result_status = Column(String, nullable=False)   # "approved" | "rejected"
    session_id = Column(String, nullable=False)
    thread_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


def create_db() -> None:
    Base.metadata.create_all(bind=engine)
