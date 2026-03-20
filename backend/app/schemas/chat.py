from pydantic import BaseModel
from typing import Optional


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class SourceRef(BaseModel):
    doc_id: str
    title: str
    excerpt: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[list[ChatMessage]] = None
    strict_mode: bool = True


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    session_id: str
