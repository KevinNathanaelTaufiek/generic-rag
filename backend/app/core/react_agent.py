import uuid
import time
import logging
from typing import Annotated, Any

from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from app.core.llm import get_llm
from app.core.tools import TOOLS, get_tools, SEARCH_KNOWLEDGE_TOOL
from app.schemas.chat import ToolCallInfo

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    sources: list[dict]
    enabled_tools: list[str]
    strict_mode: bool


# Shared MemorySaver — persists for the process lifetime (in-memory, MVP only)
_memory = MemorySaver()


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
    if tool_name == "search_knowledge":
        return f"Searching knowledge base for: \"{tool_args.get('query', '')}\""
    if tool_name == "search_web":
        return f"Searching web for: \"{tool_args.get('query', '')}\""
    if tool_name == "send_notification":
        return f"Sending notification to '{tool_args.get('to', '')}': {tool_args.get('message', '')}"
    if tool_name == "crud_data":
        return f"Performing '{tool_args.get('action', '')}' on resource '{tool_args.get('resource', '')}'"
    if tool_name == "get_random_number":
        return f"Generating random number between {tool_args.get('min', 1)} and {tool_args.get('max', 100)}"
    return f"Calling {tool_name} with args {tool_args}"


def _build_system_prompt(enabled_tools: list[str] | None, strict_mode: bool = False) -> str:
    has_knowledge = enabled_tools is None or "search_knowledge" in (enabled_tools or [])
    has_other_tools = any(t != "search_knowledge" for t in (enabled_tools or []))

    if has_knowledge and strict_mode:
        return (
            "You are a helpful assistant. Answer the user's question based ONLY on the knowledge base. "
            "Always call `search_knowledge` to retrieve relevant information before answering. "
            "If the knowledge base does not contain enough information to answer, say so clearly. "
            "Do NOT use general knowledge or make up information."
        )
    if has_knowledge and has_other_tools:
        return (
            "You are a helpful assistant with access to a knowledge base and other tools. "
            "IMPORTANT: Always call the `search_knowledge` tool FIRST for any question or task. "
            "Use the knowledge base results as your primary source of information. "
            "Only use other tools if the knowledge base does not contain sufficient information. "
            "When tool results are available, use them directly to answer — do not say you cannot answer."
        )
    if has_knowledge:
        return (
            "You are a helpful assistant. Always call `search_knowledge` first to retrieve relevant information. "
            "Use the knowledge base as your primary source. "
            "If the knowledge base returns no relevant results, do NOT call any tool again — "
            "answer directly from your own training knowledge and clearly state the answer is not from the knowledge base."
        )
    if has_other_tools:
        return (
            "You are a helpful assistant with access to tools. "
            "When a tool returns results, use those results directly to answer the user. "
            "Do not say you cannot answer if tool results are available."
        )
    return "You are a helpful assistant. Answer the user's question to the best of your ability."


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
    logger.info("[agent] node started | strict=%s | tools=%s | only_knowledge=%s", strict_mode, enabled_tools, only_knowledge)

    # --- Fast path: skip LLM #1 when only knowledge base is active ---
    if only_knowledge or (strict_mode and "search_knowledge" in enabled_tools):
        user_query = _extract_text(state["messages"][-1].content)
        logger.info("[agent] fast path: skipping LLM #1, directly executing search_knowledge")

        t1 = time.perf_counter()
        result_str = await SEARCH_KNOWLEDGE_TOOL.ainvoke({"query": user_query})
        logger.info("[agent] tool 'search_knowledge' took %.2fs | result_len=%d", time.perf_counter() - t1, len(result_str))

        sources = _extract_sources_from_tool_result(result_str)
        no_results = "[source:" not in result_str

        messages = list(state["messages"])
        if no_results and not strict_mode:
            system_prompt = (
                "You are a helpful assistant. "
                "The knowledge base did not contain relevant information for the user's question. "
                "Answer using your general training knowledge, and clearly state the answer is not from the knowledge base."
            )
        else:
            system_prompt = _build_system_prompt(enabled_tools, strict_mode)
            system_prompt += f"\n\nKnowledge base results:\n{result_str}"

        messages[0] = SystemMessage(content=system_prompt)

        t2 = time.perf_counter()
        response = await llm.ainvoke(messages)
        logger.info("[agent] LLM call #1 (answer generation, fast path) took %.2fs", time.perf_counter() - t2)
        logger.info("[agent] total node time %.2fs", time.perf_counter() - t0)
        return {**state, "messages": [response], "sources": sources}

    # --- Normal ReAct path: LLM decides which tool to call ---
    active_tools = get_tools(enabled_tools)
    llm_with_tools = llm.bind_tools(active_tools)

    messages = list(state["messages"])
    messages[0] = SystemMessage(content=_build_system_prompt(enabled_tools, strict_mode))

    t1 = time.perf_counter()
    response = await llm_with_tools.ainvoke(messages)
    logger.info("[agent] LLM call #1 (decision) took %.2fs | tool_calls=%s", time.perf_counter() - t1, [tc["name"] for tc in response.tool_calls])

    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_map = {t.name: t for t in active_tools}

        # search_knowledge executes automatically — no approval needed
        if tool_call["name"] != SEARCH_KNOWLEDGE_TOOL.name:
            pending_info = {
                "id": tool_call["id"],
                "tool_name": tool_call["name"],
                "tool_args": tool_call["args"],
            }

            approved: bool = interrupt(pending_info)

            if not approved:
                cancel_msg = HumanMessage(
                    content="User cancelled tool execution. Ask the user what went wrong or how it should be done differently."
                )
                t3 = time.perf_counter()
                clarification = await llm_with_tools.ainvoke(state["messages"] + [response, cancel_msg])
                logger.info("[agent] LLM call #2 (cancel clarification) took %.2fs", time.perf_counter() - t3)
                return {**state, "messages": [response, cancel_msg, clarification]}

        tool = tool_map.get(tool_call["name"])

        if tool is None:
            result_str = f"Error: Unknown tool '{tool_call['name']}'"
        else:
            try:
                t3 = time.perf_counter()
                result_str = await tool.ainvoke(tool_call["args"])
                logger.info("[agent] tool '%s' took %.2fs | result_len=%d", tool_call["name"], time.perf_counter() - t3, len(result_str))
            except Exception as e:
                result_str = f"Error: Tool execution failed — {str(e)}"
                logger.error("[agent] tool '%s' failed: %s", tool_call["name"], e)

        tool_message = ToolMessage(content=result_str, tool_call_id=tool_call["id"])

        sources = list(state.get("sources") or [])
        if tool_call["name"] == SEARCH_KNOWLEDGE_TOOL.name:
            sources = _extract_sources_from_tool_result(result_str)

        # Build running message history for multi-tool loop
        accumulated_messages = list(state["messages"]) + [response, tool_message]
        accumulated_new = [response, tool_message]

        # Loop: allow LLM to call additional tools (e.g. search_web after search_knowledge)
        MAX_TOOL_ROUNDS = 5
        for _round in range(MAX_TOOL_ROUNDS - 1):
            t4 = time.perf_counter()
            follow_up = await llm_with_tools.ainvoke(accumulated_messages)
            logger.info("[agent] LLM call (round %d) took %.2fs | tool_calls=%s", _round + 2, time.perf_counter() - t4, [tc["name"] for tc in follow_up.tool_calls])

            if not follow_up.tool_calls:
                accumulated_new.append(follow_up)
                break

            next_tool_call = follow_up.tool_calls[0]

            # Approval gate for non-knowledge tools
            if next_tool_call["name"] != SEARCH_KNOWLEDGE_TOOL.name:
                pending_info = {
                    "id": next_tool_call["id"],
                    "tool_name": next_tool_call["name"],
                    "tool_args": next_tool_call["args"],
                }
                approved: bool = interrupt(pending_info)
                if not approved:
                    cancel_msg = HumanMessage(
                        content="User cancelled tool execution. Ask the user what went wrong or how it should be done differently."
                    )
                    clarification = await llm_with_tools.ainvoke(accumulated_messages + [follow_up, cancel_msg])
                    accumulated_new.extend([follow_up, cancel_msg, clarification])
                    break

            next_tool = tool_map.get(next_tool_call["name"])
            if next_tool is None:
                next_result = f"Error: Unknown tool '{next_tool_call['name']}'"
            else:
                try:
                    t5 = time.perf_counter()
                    next_result = await next_tool.ainvoke(next_tool_call["args"])
                    logger.info("[agent] tool '%s' took %.2fs | result_len=%d", next_tool_call["name"], time.perf_counter() - t5, len(next_result))
                except Exception as e:
                    next_result = f"Error: Tool execution failed — {str(e)}"
                    logger.error("[agent] tool '%s' failed: %s", next_tool_call["name"], e)

            next_tool_message = ToolMessage(content=next_result, tool_call_id=next_tool_call["id"])
            if next_tool_call["name"] == SEARCH_KNOWLEDGE_TOOL.name:
                sources = _extract_sources_from_tool_result(next_result)

            accumulated_messages.extend([follow_up, next_tool_message])
            accumulated_new.extend([follow_up, next_tool_message])
        else:
            # Hit MAX_TOOL_ROUNDS without a final answer — generate one
            t4 = time.perf_counter()
            follow_up = await llm_with_tools.ainvoke(accumulated_messages)
            logger.info("[agent] LLM final answer after max rounds took %.2fs", time.perf_counter() - t4)
            accumulated_new.append(follow_up)

        logger.info("[agent] total node time %.2fs", time.perf_counter() - t0)
        return {**state, "messages": accumulated_new, "sources": sources}

    # No tool call — direct answer
    logger.info("[agent] no tool call, direct answer | total %.2fs", time.perf_counter() - t0)
    return {**state, "messages": [response]}


def _compile_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    # Note: interrupt() is called dynamically inside agent_node — do NOT use interrupt_before here
    return graph.compile(checkpointer=_memory)


_agent_graph = _compile_graph()


async def run_agent(message: str, history: list[dict], session_id: str, enabled_tools: list[str] | None = None, strict_mode: bool = False) -> dict[str, Any]:
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
    for turn in history:
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=message))

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await _agent_graph.ainvoke(
        {"messages": messages, "sources": [], "enabled_tools": enabled_tools or [], "strict_mode": strict_mode},
        config,
    )

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

    return {
        "status": "done",
        "answer": answer,
        "sources": result.get("sources", []),
        "thread_id": None,
        "pending_tool": None,
        "session_id": session_id,
    }


async def resume_agent(thread_id: str, approved: bool, session_id: str) -> dict[str, Any]:
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

    # Resume: Command(resume=approved) is passed back as the return value of interrupt()
    result = await _agent_graph.ainvoke(Command(resume=approved), config)

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

    return {
        "status": "done",
        "answer": answer,
        "sources": result.get("sources", []),
        "thread_id": None,
        "pending_tool": None,
        "session_id": session_id,
    }
