import uuid
from fastapi import APIRouter, HTTPException

from app.schemas.chat import (
    ChatRequest, ChatResponse,
    ToolApprovalRequest, ToolApprovalResponse,
    SourceRef,
)
from app.core.react_agent import run_agent, resume_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    history = [msg.model_dump() for msg in (body.history or [])]

    result = await run_agent(
        message=body.message,
        history=history,
        session_id=session_id,
        enabled_tools=body.enabled_tools,
        strict_mode=body.strict_mode,
    )

    sources = [SourceRef(**s) for s in result.get("sources", [])]

    return ChatResponse(
        answer=result["answer"],
        sources=sources,
        session_id=session_id,
        status=result["status"],
        pending_tool=result.get("pending_tool"),
        thread_id=result.get("thread_id"),
    )


@router.post("/tool-approval", response_model=ToolApprovalResponse)
async def tool_approval(body: ToolApprovalRequest):
    try:
        result = await resume_agent(
            thread_id=body.thread_id,
            approved=body.approved,
            session_id=body.session_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Tool approval expired or not found: {str(e)}",
        )

    sources = [SourceRef(**s) for s in result.get("sources", [])]

    return ToolApprovalResponse(
        answer=result["answer"],
        sources=sources,
        session_id=body.session_id,
        status=result["status"],
        pending_tool=result.get("pending_tool"),
        thread_id=result.get("thread_id"),
    )
