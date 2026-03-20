import uuid
from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse, SourceRef
from app.core.rag_chain import rag_graph

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest):
    session_id = body.session_id or str(uuid.uuid4())
    history = [msg.model_dump() for msg in (body.history or [])]

    state = rag_graph.invoke({
        "question": body.message,
        "history": history,
        "context_docs": [],
        "answer": "",
        "sources": [],
        "strict_mode": body.strict_mode,
    })

    sources = [SourceRef(**s) for s in state["sources"]]

    return ChatResponse(
        answer=state["answer"],
        sources=sources,
        session_id=session_id,
    )
