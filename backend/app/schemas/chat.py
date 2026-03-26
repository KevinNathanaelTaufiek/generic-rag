from pydantic import BaseModel
from typing import Literal, Optional


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class SourceRef(BaseModel):
    doc_id: str
    title: str
    excerpt: str
    url: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[list[ChatMessage]] = None
    strict_mode: bool = True
    enabled_tools: Optional[list[str]] = None  # None = all tools enabled


class ToolCallInfo(BaseModel):
    tool_name: str
    tool_args: dict
    description: str  # human-readable summary for UI


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    session_id: str
    status: Literal["done", "pending_tool_approval"] = "done"
    pending_tool: Optional[ToolCallInfo] = None
    thread_id: Optional[str] = None
    from_general_knowledge: bool = False


class ToolApprovalRequest(BaseModel):
    thread_id: str
    session_id: str
    approved: bool
    modified_args: Optional[dict] = None  # user-edited args, None if unchanged


class ToolApprovalResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    session_id: str
    status: Literal["done", "pending_tool_approval"] = "done"
    pending_tool: Optional[ToolCallInfo] = None
    thread_id: Optional[str] = None
    from_general_knowledge: bool = False
