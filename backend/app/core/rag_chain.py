from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.core.vectorstore import get_vectorstore
from app.config import settings


class RAGState(TypedDict):
    question: str
    history: list[dict]
    context_docs: list[dict]
    answer: str
    sources: list[dict]
    strict_mode: bool


def retrieve_node(state: RAGState) -> RAGState:
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search_with_relevance_scores(
        state["question"],
        k=settings.top_k_results,
    )

    context_docs = []
    for doc, score in results:
        context_docs.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": score,
        })

    return {**state, "context_docs": context_docs}


def generate_node(state: RAGState) -> RAGState:
    llm = get_llm()

    context_text = "\n\n---\n\n".join(
        doc["content"] for doc in state["context_docs"]
    )

    strict_mode = state.get("strict_mode", True)
    if strict_mode:
        system_prompt = (
            "You are a helpful assistant. Answer the user's question based ONLY on the "
            "provided context below. If the context does not contain enough information "
            "to answer the question, say so clearly. Do not make up information.\n\n"
            f"Context:\n{context_text}"
        )
    else:
        system_prompt = (
            "You are a helpful assistant. Use the provided context below as your primary "
            "source of information. If the context is relevant, prioritize it in your answer. "
            "If the context is not relevant or insufficient, you may use your general knowledge "
            "to help the user.\n\n"
            f"Context:\n{context_text}"
        )

    messages = [SystemMessage(content=system_prompt)]
    for turn in (state.get("history") or []):
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=state["question"]))

    response = llm.invoke(messages)

    sources = []
    seen_doc_ids = set()
    for doc in state["context_docs"]:
        doc_id = doc["metadata"].get("doc_id", "")
        if doc_id and doc_id not in seen_doc_ids:
            seen_doc_ids.add(doc_id)
            sources.append({
                "doc_id": doc_id,
                "title": doc["metadata"].get("title", "Unknown"),
                "excerpt": doc["content"][:200],
            })

    return {**state, "answer": response.content, "sources": sources}


def build_rag_graph() -> StateGraph:
    graph = StateGraph(RAGState)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()


rag_graph = build_rag_graph()
