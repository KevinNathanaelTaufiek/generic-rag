from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = "sqlite:///./data/audit.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


class AuditRecord(Base):
    __tablename__ = "audit"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False, index=True)   # tool name OR "knowledge.add" | "knowledge.delete"
    details = Column(JSON, nullable=False)                # tool args OR doc metadata
    changes = Column(JSON, nullable=True)                 # user-edited args (tool calls only)
    status = Column(String, nullable=False)               # "approved" | "rejected" | "completed"
    session_id = Column(String, nullable=False)
    thread_id = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))


class KnowledgeContent(Base):
    __tablename__ = "knowledge_content"

    doc_id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(String, nullable=False)


def create_db() -> None:
    Base.metadata.create_all(bind=engine)
