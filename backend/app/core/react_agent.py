import uuid
import time
import asyncio
import logging
import json
from contextvars import ContextVar
from typing import Annotated, Any, Callable, Optional

from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from app.config import settings
from app.core.llm import get_llm
from app.core.tools import get_tools, SEARCH_KNOWLEDGE_TOOL
from app.schemas.chat import ToolCallInfo

logger = logging.getLogger(__name__)

# Per-request progress callback — set via contextvars so it's isolated per async task (per user/request)
_current_progress_cb: ContextVar[Optional[Callable]] = ContextVar("_current_progress_cb", default=None)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    sources: list[dict]
    enabled_tools: list[str]
    strict_mode: bool
    from_general_knowledge: bool


# Shared MemorySaver — persists for the process lifetime (in-memory, MVP only)
# TODO(prod): ganti ke AsyncRedisSaver (langgraph-checkpoint-redis) untuk multi-instance
# dan survive restart. TTL manual di bawah bisa dihapus, pakai native TTL Redis.
_memory = MemorySaver()

THREAD_TTL_SECONDS = 3600  # 1 hour

def _schedule_thread_cleanup(thread_id: str) -> None:
    """Schedule deletion of a thread after TTL expires (handles abandoned approval requests)."""
    async def _cleanup():
        await asyncio.sleep(THREAD_TTL_SECONDS)
        _memory.delete_thread(thread_id)
        logger.debug("[agent] TTL cleanup: deleted thread %s", thread_id)

    asyncio.ensure_future(_cleanup())


def _extract_text(content) -> str:
    """Extract plain string from LangChain message content (handles Gemini list format)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
        return "".join(parts)
    return str(content)


def _build_description(tool_name: str, tool_args: dict) -> str:
    if not tool_args:
        return f"Calling {tool_name}"
    args_str = ", ".join(f"{k}={repr(v)}" for k, v in tool_args.items())
    return f"{tool_name}({args_str})"


def _build_system_prompt(enabled_tools: list[str] | None, strict_mode: bool = False) -> str:
    has_knowledge = enabled_tools is None or "search_knowledge" in (enabled_tools or [])
    has_other_tools = any(t != "search_knowledge" for t in (enabled_tools or []))

    if has_knowledge and strict_mode:
        return (
            "You are a helpful assistant. Answer the user's question based ONLY on the knowledge base. "
            "Always call `search_knowledge` to retrieve relevant information before answering. "
            "If the user's question covers multiple distinct topics, call `search_knowledge` once per topic and collect ALL results before composing your answer. "
            "After getting results: answer ONLY the parts of the question that are explicitly covered in the knowledge base results. "
            "For parts of the question NOT found in the knowledge base, clearly state that specific information is not available — but still answer the parts that ARE found. "
            "Do NOT use general knowledge or make up information for any part of your answer."
        )
    if has_knowledge and has_other_tools:
        return (
            "You are a helpful assistant with access to a knowledge base and other tools. "
            "IMPORTANT: Always call the `search_knowledge` tool FIRST for any question or task. "
            "If the user's question covers multiple distinct topics, call `search_knowledge` once per topic and collect ALL results before composing your answer. "
            "Use the knowledge base results as your primary source of information. "
            "Use other tools if the knowledge base does not contain sufficient information. "
            "When tool results are available, use them directly to answer — do not say you cannot answer. "
            "If your answer is based entirely on your own training knowledge (not from any tool result), start your response with the exact token [GENERAL_KNOWLEDGE] on its own line."
        )
    if has_knowledge:
        return (
            "You are a helpful assistant. Always call `search_knowledge` first to retrieve relevant information. "
            "If the user's question covers multiple distinct topics, call `search_knowledge` once per topic and collect ALL results before composing your answer. "
            "Use the knowledge base as your primary source. "
            "If the knowledge base returns no relevant results, do NOT call `search_knowledge` tool again — instead "
            "use your own training knowledge to answer. "
            "If your answer is based entirely on your own training knowledge (not from any tool result), start your response with the exact token [GENERAL_KNOWLEDGE] on its own line."
        )
    if has_other_tools:
        return (
            "You are a helpful assistant with access to tools. "
            "When a tool returns results, use those results directly to answer the user. "
            "Use the tool results as your primary source. "
            "If your answer is based entirely on your own training knowledge (not from any tool result), start your response with the exact token [GENERAL_KNOWLEDGE] on its own line."
        )
    return (
        "You are a helpful assistant. Answer the user's question to the best of your ability. "
        "Since you have no tools available, start your response with the exact token [GENERAL_KNOWLEDGE] on its own line."
    )


def _extract_sources_from_web_result(result_str: str) -> list[dict]:
    """Parse sources from search_web tool output (JSON block)."""
    try:
        start = result_str.find("[web_sources_json]\n")
        end = result_str.find("\n[/web_sources_json]")
        if start == -1 or end == -1:
            return []
        json_str = result_str[start + len("[web_sources_json]\n"):end]
        items = json.loads(json_str)
        return [
            {"doc_id": f"web:{i}", "title": r["title"], "excerpt": r["content"][:200], "url": r["url"]}
            for i, r in enumerate(items)
        ]
    except Exception:
        return []


def _extract_sources_from_tool_result(result_str: str) -> list[dict]:
    """Parse sources from search_knowledge tool output."""
    sources = []
    seen = set()
    for block in result_str.split("\n\n---\n\n"):
        first_line = block.strip().splitlines()[0] if block.strip() else ""
        if not first_line.startswith("[source:"):
            continue
        # Format: [source: {title} | doc_id: {doc_id} | score: {score}]
        inner = first_line.lstrip("[").rstrip("]")
        parts = {p.split(":")[0].strip(): ":".join(p.split(":")[1:]).strip() for p in inner.split("|")}
        doc_id = parts.get("doc_id", "")
        title = parts.get("source", "Unknown")
        excerpt = "\n".join(block.strip().splitlines()[1:])[:200]
        if doc_id and doc_id not in seen:
            seen.add(doc_id)
            sources.append({"doc_id": doc_id, "title": title, "excerpt": excerpt})
    return sources


async def agent_node(state: AgentState) -> AgentState:
    t0 = time.perf_counter()
    llm = get_llm()
    enabled_tools = state.get("enabled_tools") or []
    strict_mode = state.get("strict_mode", False)
    only_knowledge = "search_knowledge" in enabled_tools and not any(t != "search_knowledge" for t in enabled_tools)
    # Per-request progress callback — injected by run_agent/resume_agent, never stored in state
    _progress_cb = _current_progress_cb.get()
    logger.info("[agent] node started | strict=%s | tools=%s | only_knowledge=%s", strict_mode, enabled_tools, only_knowledge)

    async def _emit(event: str, label: str):
        if _progress_cb:
            await _progress_cb({"event": event, "label": label})

    async def _stream_llm(bound_llm, messages_arg) -> Any:
        """Stream an LLM call, emit thinking/answer tokens, return accumulated response."""
        full = None
        async for chunk in bound_llm.astream(messages_arg):
            full = chunk if full is None else full + chunk
            # Multi-model safe: OpenAI returns str, Gemini returns list of blocks
            if isinstance(chunk.content, str):
                if chunk.content:
                    await _emit("answer_token", chunk.content)
            elif isinstance(chunk.content, list):
                for block in chunk.content:
                    if isinstance(block, dict):
                        if block.get("type") == "thinking" and block.get("thinking"):
                            await _emit("thinking_token", block["thinking"])
                        elif block.get("type") == "text" and block.get("text"):
                            await _emit("answer_token", block["text"])
        return full

    # --- Fast path: skip LLM #1 when only knowledge base is active ---
    # To re-enable: uncomment this block and comment out the ReAct path below
    # if only_knowledge or (strict_mode and "search_knowledge" in enabled_tools):
    #     user_query = _extract_text(state["messages"][-1].content)
    #
    #     logger.info("[agent] fast path: skipping LLM #1, directly executing search_knowledge")
    #
    #     t1 = time.perf_counter()
    #     result_str = await SEARCH_KNOWLEDGE_TOOL.ainvoke({"query": user_query})
    #     logger.info("[agent] tool 'search_knowledge' took %.2fs | result_len=%d", time.perf_counter() - t1, len(result_str))
    #
    #     sources = _extract_sources_from_tool_result(result_str)
    #     no_results = "[source:" not in result_str
    #
    #     if no_results and strict_mode:
    #         logger.info("[agent] strict mode: no knowledge base results, refusing to answer from general knowledge")
    #         return {
    #             **state,
    #             "messages": [AIMessage(content="Maaf, informasi tersebut tidak ditemukan di knowledge base. Saya tidak dapat menjawab pertanyaan ini berdasarkan sumber yang tersedia.")],
    #             "sources": [],
    #         }
    #
    #     messages = list(state["messages"])
    #     if no_results and not strict_mode:
    #         system_prompt = (
    #             "You are a helpful assistant. "
    #             "The knowledge base did not contain relevant information for the user's question. "
    #             "Answer using your general training knowledge, and clearly state the answer is not from the knowledge base."
    #         )
    #     else:
    #         system_prompt = _build_system_prompt(enabled_tools, strict_mode)
    #         system_prompt += f"\n\nKnowledge base results:\n{result_str}"
    #
    #     messages[0] = SystemMessage(content=system_prompt)
    #
    #     t2 = time.perf_counter()
    #     response = await llm.ainvoke(messages)
    #     logger.info("[agent] LLM call #1 (answer generation, fast path) took %.2fs", time.perf_counter() - t2)
    #     logger.info("[agent] total node time %.2fs", time.perf_counter() - t0)
    #     return {**state, "messages": [response], "sources": sources}

    # --- ReAct path: LLM decides which tool to call (supports multi-turn context) ---
    # To re-enable fast path: comment out this block and uncomment the fast path above
    active_tools = get_tools(enabled_tools)
    llm_with_tools = llm.bind_tools(active_tools)

    messages = list(state["messages"])
    messages[0] = SystemMessage(content=_build_system_prompt(enabled_tools, strict_mode))

    await _emit("thinking", "Thinking…")
    t1 = time.perf_counter()
    response = await _stream_llm(llm_with_tools, messages)
    logger.info("[agent] LLM call #1 (decision) took %.2fs | tool_calls=%s", time.perf_counter() - t1, [tc["name"] for tc in response.tool_calls])

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_map = {t.name: t for t in active_tools}

        # search_knowledge executes automatically — no approval needed
        effective_args = tool_call["args"]

        if tool_call["name"] != SEARCH_KNOWLEDGE_TOOL.name:
            pending_info = {
                "id": tool_call["id"],
                "tool_name": tool_call["name"],
                "tool_args": tool_call["args"],
            }

            approval_result = interrupt(pending_info)

            if isinstance(approval_result, dict):
                is_approved = approval_result.get("approved", False)
                effective_args = approval_result.get("modified_args") or tool_call["args"]
            else:
                is_approved = bool(approval_result)

            if not is_approved:
                cancel_msg = HumanMessage(
                    content="User cancelled tool execution. Ask the user what went wrong or how it should be done differently."
                )
                await _emit("generating", "Generating response…")
                t3 = time.perf_counter()
                clarification = await _stream_llm(llm_with_tools, state["messages"] + [response, cancel_msg])
                logger.info("[agent] LLM call #2 (cancel clarification) took %.2fs", time.perf_counter() - t3)
                return {**state, "messages": [response, cancel_msg, clarification]}

        _tool_labels = {
            SEARCH_KNOWLEDGE_TOOL.name: "Searching knowledge base…",
            "search_web": "Searching the web…",
        }
        await _emit("tool_executing", _tool_labels.get(tool_call["name"], f"Running {tool_call['name']}…"))

        tool = tool_map.get(tool_call["name"])

        if tool is None:
            result_str = f"Error: Unknown tool '{tool_call['name']}'"
        else:
            try:
                t3 = time.perf_counter()
                result_str = await tool.ainvoke(effective_args)
                logger.info("[agent] tool '%s' took %.2fs | result_len=%d", tool_call["name"], time.perf_counter() - t3, len(result_str))
            except Exception as e:
                result_str = f"Error: Tool execution failed — {str(e)}"
                logger.error("[agent] tool '%s' failed: %s", tool_call["name"], e)

        tool_message = ToolMessage(content=result_str, tool_call_id=tool_call["id"])

        sources = list(state.get("sources") or [])
        if tool_call["name"] == SEARCH_KNOWLEDGE_TOOL.name:
            new_sources = _extract_sources_from_tool_result(result_str)
            sources = sources + new_sources
            # Strict mode: refuse immediately if knowledge base has no results
            if strict_mode and not new_sources:
                logger.info("[agent] strict mode: search_knowledge returned no results, refusing answer")
                refusal = AIMessage(content="Maaf, informasi tersebut tidak ditemukan di knowledge base. Saya tidak dapat menjawab pertanyaan ini berdasarkan sumber yang tersedia.")
                return {**state, "messages": [response, tool_message, refusal], "sources": [], "from_general_knowledge": False}
        elif tool_call["name"] == "search_web":
            sources = sources + _extract_sources_from_web_result(result_str)

        # Build running message history for multi-tool loop
        accumulated_messages = list(state["messages"]) + [response, tool_message]
        accumulated_new = [response, tool_message]

        # Loop: allow LLM to call additional tools (e.g. search_web after search_knowledge)
        MAX_TOOL_ROUNDS = 5
        for _round in range(MAX_TOOL_ROUNDS - 1):
            await _emit("thinking", "Thinking…")
            t4 = time.perf_counter()
            follow_up = await _stream_llm(llm_with_tools, accumulated_messages)
            logger.info("[agent] LLM call (round %d) took %.2fs | tool_calls=%s", _round + 2, time.perf_counter() - t4, [tc["name"] for tc in follow_up.tool_calls])

            if not follow_up.tool_calls:
                await _emit("generating", "Generating response…")
                accumulated_new.append(follow_up)
                break

            next_tool_call = follow_up.tool_calls[0]

            # Approval gate for non-knowledge tools
            next_effective_args = next_tool_call["args"]
            if next_tool_call["name"] != SEARCH_KNOWLEDGE_TOOL.name:
                pending_info = {
                    "id": next_tool_call["id"],
                    "tool_name": next_tool_call["name"],
                    "tool_args": next_tool_call["args"],
                }
                next_approval_result = interrupt(pending_info)
                if isinstance(next_approval_result, dict):
                    next_is_approved = next_approval_result.get("approved", False)
                    next_effective_args = next_approval_result.get("modified_args") or next_tool_call["args"]
                else:
                    next_is_approved = bool(next_approval_result)

                if not next_is_approved:
                    cancel_msg = HumanMessage(
                        content="User cancelled tool execution. Ask the user what went wrong or how it should be done differently."
                    )
                    await _emit("generating", "Generating response…")
                    clarification = await _stream_llm(llm_with_tools, accumulated_messages + [follow_up, cancel_msg])
                    accumulated_new.extend([follow_up, cancel_msg, clarification])
                    break

            await _emit("tool_executing", _tool_labels.get(next_tool_call["name"], f"Running {next_tool_call['name']}…"))
            next_tool = tool_map.get(next_tool_call["name"])
            if next_tool is None:
                next_result = f"Error: Unknown tool '{next_tool_call['name']}'"
            else:
                try:
                    t5 = time.perf_counter()
                    next_result = await next_tool.ainvoke(next_effective_args)
                    logger.info("[agent] tool '%s' took %.2fs | result_len=%d", next_tool_call["name"], time.perf_counter() - t5, len(next_result))
                except Exception as e:
                    next_result = f"Error: Tool execution failed — {str(e)}"
                    logger.error("[agent] tool '%s' failed: %s", next_tool_call["name"], e)

            next_tool_message = ToolMessage(content=next_result, tool_call_id=next_tool_call["id"])
            if next_tool_call["name"] == SEARCH_KNOWLEDGE_TOOL.name:
                sources = sources + _extract_sources_from_tool_result(next_result)
            elif next_tool_call["name"] == "search_web":
                sources = sources + _extract_sources_from_web_result(next_result)

            accumulated_messages.extend([follow_up, next_tool_message])
            accumulated_new.extend([follow_up, next_tool_message])
        else:
            # Hit MAX_TOOL_ROUNDS without a final answer — generate one
            await _emit("generating", "Generating response…")
            t4 = time.perf_counter()
            follow_up = await _stream_llm(llm_with_tools, accumulated_messages)
            logger.info("[agent] LLM final answer after max rounds took %.2fs", time.perf_counter() - t4)
            accumulated_new.append(follow_up)

        logger.info("[agent] total node time %.2fs", time.perf_counter() - t0)
        return {**state, "messages": accumulated_new, "sources": sources, "from_general_knowledge": False}

    # No tool call — direct answer
    # In strict mode, LLM must always call search_knowledge first
    if strict_mode and "search_knowledge" in enabled_tools:
        logger.info("[agent] strict mode: LLM skipped tool call, refusing direct answer")
        refusal = AIMessage(content="Maaf, saya tidak dapat menjawab pertanyaan ini. Tidak ada informasi yang relevan ditemukan di knowledge base.")
        return {**state, "messages": [refusal], "from_general_knowledge": False}

    logger.info("[agent] no tool call, direct answer from general knowledge | total %.2fs", time.perf_counter() - t0)
    return {**state, "messages": [response], "from_general_knowledge": True}


def _compile_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    # Note: interrupt() is called dynamically inside agent_node — do NOT use interrupt_before here
    return graph.compile(checkpointer=_memory)


_agent_graph = _compile_graph()


async def run_agent(message: str, history: list[dict], session_id: str, enabled_tools: list[str] | None = None, strict_mode: bool = False, progress_cb: Optional[Callable] = None) -> dict[str, Any]:
    """
    Start a new agent turn. Returns a dict with:
    - status: "done" | "pending_tool_approval"
    - answer: str (empty if pending)
    - sources: list
    - thread_id: str | None (set if pending, for use in resume_agent)
    - pending_tool: ToolCallInfo | None
    - session_id: str
    """
    # Placeholder system message — agent_node replaces this dynamically based on enabled_tools
    messages = [SystemMessage(content="")]
    trimmed_history = history[-(settings.max_history_turns * 2):]
    for turn in trimmed_history:
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=message))

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    token = _current_progress_cb.set(progress_cb)
    try:
        result = await _agent_graph.ainvoke(
            {"messages": messages, "sources": [], "enabled_tools": enabled_tools or [], "strict_mode": strict_mode},
            config,
        )
    finally:
        _current_progress_cb.reset(token)

    # Check if graph was interrupted (tool approval needed)
    state_snapshot = _agent_graph.get_state(config)
    if state_snapshot.next:
        # Extract interrupt payload — contains pending tool call info
        interrupts = []
        if state_snapshot.tasks:
            interrupts = state_snapshot.tasks[0].interrupts
        pending_info = interrupts[0].value if interrupts else {}

        tool_info = ToolCallInfo(
            tool_name=pending_info.get("tool_name", ""),
            tool_args=pending_info.get("tool_args", {}),
            description=_build_description(
                pending_info.get("tool_name", ""),
                pending_info.get("tool_args", {}),
            ),
        )
        _schedule_thread_cleanup(thread_id)
        return {
            "status": "pending_tool_approval",
            "answer": "",
            "sources": [],
            "thread_id": thread_id,
            "pending_tool": tool_info,
            "session_id": session_id,
        }

    # Completed without interruption
    final_message = result["messages"][-1]
    answer = _extract_text(final_message.content) if hasattr(final_message, "content") else str(final_message)

    # Check marker before stripping — LLM explicitly signals general knowledge usage
    from_general_knowledge = "[GENERAL_KNOWLEDGE]" in answer
    answer = answer.replace("[GENERAL_KNOWLEDGE]", "").lstrip("\n").strip()

    sources = result.get("sources", [])

    _memory.delete_thread(thread_id)

    return {
        "status": "done",
        "answer": answer,
        "sources": sources,
        "from_general_knowledge": from_general_knowledge,
        "thread_id": None,
        "pending_tool": None,
        "session_id": session_id,
    }


def get_pending_info(thread_id: str) -> dict:
    """Return the pending interrupt payload for a paused thread (for audit logging)."""
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = _agent_graph.get_state(config)
    if state_snapshot.tasks and state_snapshot.tasks[0].interrupts:
        return state_snapshot.tasks[0].interrupts[0].value
    return {}


async def resume_agent(thread_id: str, approved: bool, session_id: str, modified_args: Optional[dict] = None, progress_cb: Optional[Callable] = None) -> dict[str, Any]:
    """
    Resume a paused agent after user approves or cancels tool execution.
    Uses Command(resume=approved) — the interrupt() return value in agent_node will be `approved`.
    Raises ValueError if thread_id not found or not in a paused state.
    """
    config = {"configurable": {"thread_id": thread_id}}

    # Verify thread exists and is paused
    state_snapshot = _agent_graph.get_state(config)
    if not state_snapshot.next:
        raise ValueError(f"No pending approval found for thread_id={thread_id}")

    # Resume: build resume value — dict if user edited args, bool otherwise
    if approved and modified_args:
        resume_value: bool | dict = {"approved": True, "modified_args": modified_args}
    else:
        resume_value = approved

    token = _current_progress_cb.set(progress_cb)
    try:
        result = await _agent_graph.ainvoke(Command(resume=resume_value), config)
    finally:
        _current_progress_cb.reset(token)

    # Check if interrupted again (another tool call)
    state_snapshot = _agent_graph.get_state(config)
    if state_snapshot.next:
        interrupts = state_snapshot.tasks[0].interrupts if state_snapshot.tasks else []
        pending_info = interrupts[0].value if interrupts else {}

        tool_info = ToolCallInfo(
            tool_name=pending_info.get("tool_name", ""),
            tool_args=pending_info.get("tool_args", {}),
            description=_build_description(
                pending_info.get("tool_name", ""),
                pending_info.get("tool_args", {}),
            ),
        )
        return {
            "status": "pending_tool_approval",
            "answer": "",
            "sources": [],
            "thread_id": thread_id,  # same thread continues
            "pending_tool": tool_info,
            "session_id": session_id,
        }

    # Completed
    final_message = result["messages"][-1]
    answer = _extract_text(final_message.content) if hasattr(final_message, "content") else str(final_message)

    answer = answer.replace("[GENERAL_KNOWLEDGE]", "").lstrip("\n").strip()
    sources_list = result.get("sources", [])
    from_general_knowledge = len(sources_list) == 0 and bool(answer) and not answer.startswith("Maaf,")

    _memory.delete_thread(thread_id)

    return {
        "status": "done",
        "answer": answer,
        "sources": sources_list,
        "from_general_knowledge": from_general_knowledge,
        "thread_id": None,
        "pending_tool": None,
        "session_id": session_id,
    }
