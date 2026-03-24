import asyncio
import json
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.core.react_agent import get_pending_info, resume_agent, run_agent
from app.core.tools import TOOLS, SEARCH_KNOWLEDGE_TOOL
from app.schemas.chat import (
    ChatRequest, ChatResponse,
    SourceRef,
    ToolApprovalRequest, ToolApprovalResponse,
)
from app.services.audit import log_tool_approval

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_chat(body: ChatRequest, username: str) -> AsyncGenerator[str, None]:
    session_id = body.session_id or str(uuid.uuid4())
    history = [msg.model_dump() for msg in (body.history or [])]

    queue: asyncio.Queue = asyncio.Queue()

    async def progress_cb(payload: dict):
        await queue.put(payload)

    # Run agent in background task so we can stream progress concurrently
    agent_task = asyncio.create_task(
        run_agent(
            message=body.message,
            history=history,
            session_id=session_id,
            enabled_tools=body.enabled_tools,
            strict_mode=body.strict_mode,
            progress_cb=progress_cb,
        )
    )

    # Stream progress events while agent is running
    while not agent_task.done():
        try:
            payload = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield _sse("progress", payload)
        except asyncio.TimeoutError:
            continue

    # Drain any remaining progress events
    while not queue.empty():
        payload = queue.get_nowait()
        yield _sse("progress", payload)

    # Get final result
    result = agent_task.result()

    final = ChatResponse(
        answer=result["answer"],
        sources=[SourceRef(**s) for s in result.get("sources", [])],
        session_id=session_id,
        status=result["status"],
        pending_tool=result.get("pending_tool"),
        thread_id=result.get("thread_id"),
        from_general_knowledge=result.get("from_general_knowledge", False),
    )
    yield _sse("done", final.model_dump())


@router.get("/tools")
def list_tools():
    """Return all available tools for the frontend tool selector."""
    all_tools = [SEARCH_KNOWLEDGE_TOOL] + TOOLS
    return {
        "tools": [
            {"name": t.name, "description": t.description.split("\n")[0]}
            for t in all_tools
        ]
    }


@router.post("/stream")
async def chat_stream(body: ChatRequest, x_username: Optional[str] = Header(default="anonymous")):
    return StreamingResponse(
        _stream_chat(body, x_username or "anonymous"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, x_username: Optional[str] = Header(default="anonymous")):
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
        from_general_knowledge=result.get("from_general_knowledge", False),
    )


@router.post("/tool-approval", response_model=ToolApprovalResponse)
async def tool_approval(body: ToolApprovalRequest, x_username: Optional[str] = Header(default="anonymous")):
    # Capture pending tool info BEFORE resuming (needed for audit)
    pending_info = get_pending_info(body.thread_id)

    try:
        result = await resume_agent(
            thread_id=body.thread_id,
            approved=body.approved,
            session_id=body.session_id,
            modified_args=body.modified_args,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Tool approval expired or not found: {str(e)}",
        )

    # Log audit record
    log_tool_approval(
        username=x_username or "anonymous",
        tool_name=pending_info.get("tool_name", "unknown"),
        ai_suggested_args=pending_info.get("tool_args", {}),
        user_edited_args=body.modified_args,
        result_status="approved" if body.approved else "rejected",
        session_id=body.session_id,
        thread_id=body.thread_id,
    )

    sources = [SourceRef(**s) for s in result.get("sources", [])]

    return ToolApprovalResponse(
        answer=result["answer"],
        sources=sources,
        session_id=body.session_id,
        status=result["status"],
        pending_tool=result.get("pending_tool"),
        thread_id=result.get("thread_id"),
        from_general_knowledge=result.get("from_general_knowledge", False),
    )
