import uuid
from typing import Annotated, Any

from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from app.core.llm import get_llm
from app.core.tools import TOOLS
from app.schemas.chat import ToolCallInfo


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    sources: list[dict]


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
    if tool_name == "search_web":
        return f"Searching web for: \"{tool_args.get('query', '')}\""
    if tool_name == "send_notification":
        return f"Sending notification to '{tool_args.get('to', '')}': {tool_args.get('message', '')}"
    if tool_name == "crud_data":
        return f"Performing '{tool_args.get('action', '')}' on resource '{tool_args.get('resource', '')}'"
    return f"Calling {tool_name} with args {tool_args}"


async def agent_node(state: AgentState) -> AgentState:
    llm = get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)

    response = await llm_with_tools.ainvoke(state["messages"])

    if response.tool_calls:
        # Take the first tool call — ask user for approval via interrupt()
        tool_call = response.tool_calls[0]
        pending_info = {
            "id": tool_call["id"],
            "tool_name": tool_call["name"],
            "tool_args": tool_call["args"],
        }

        # interrupt() pauses the graph and returns the value from Command(resume=value)
        # approved will be True (proceed) or False (cancelled)
        approved: bool = interrupt(pending_info)

        if not approved:
            # User cancelled — ask for clarification
            cancel_msg = HumanMessage(
                content="User cancelled tool execution. Ask the user what went wrong or how it should be done differently."
            )
            clarification = await llm_with_tools.ainvoke(state["messages"] + [response, cancel_msg])
            return {**state, "messages": [response, cancel_msg, clarification]}

        # User approved — execute the tool
        tool_map = {t.name: t for t in TOOLS}
        tool = tool_map.get(tool_call["name"])

        if tool is None:
            result_str = f"Error: Unknown tool '{tool_call['name']}'"
        else:
            try:
                result_str = await tool.ainvoke(tool_call["args"])
            except Exception as e:
                result_str = f"Error: Tool execution failed — {str(e)}"

        tool_message = ToolMessage(
            content=result_str,
            tool_call_id=tool_call["id"],
        )

        # Continue reasoning with tool result
        follow_up = await llm_with_tools.ainvoke(state["messages"] + [response, tool_message])
        return {**state, "messages": [response, tool_message, follow_up]}

    # No tool call — direct answer
    return {**state, "messages": [response]}


def _compile_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    # Note: interrupt() is called dynamically inside agent_node — do NOT use interrupt_before here
    return graph.compile(checkpointer=_memory)


_agent_graph = _compile_graph()


async def run_agent(message: str, history: list[dict], session_id: str) -> dict[str, Any]:
    """
    Start a new agent turn. Returns a dict with:
    - status: "done" | "pending_tool_approval"
    - answer: str (empty if pending)
    - sources: list
    - thread_id: str | None (set if pending, for use in resume_agent)
    - pending_tool: ToolCallInfo | None
    - session_id: str
    """
    messages = [
        SystemMessage(content=(
            "You are a helpful assistant with access to tools. "
            "When a tool returns results, use those results directly to answer the user — "
            "even if the data looks like placeholder or demo content. "
            "Do not say you cannot answer if tool results are available."
        ))
    ]
    for turn in history:
        if turn.get("role") == "user":
            messages.append(HumanMessage(content=turn["content"]))
        else:
            messages.append(AIMessage(content=turn["content"]))
    messages.append(HumanMessage(content=message))

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = await _agent_graph.ainvoke(
        {"messages": messages, "sources": []},
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
