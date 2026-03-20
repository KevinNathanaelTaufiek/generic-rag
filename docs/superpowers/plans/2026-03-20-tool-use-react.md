# Tool Use (ReAct System) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a LangGraph ReAct agent loop to the Generic RAG system with human-in-the-loop tool approval, 3 tools (search_web, send_notification, crud_data), and a standalone dummy microservices app.

**Architecture:** The existing `rag_chain.py` stays unchanged. A new `react_agent.py` builds a LangGraph graph where `agent_node` uses LLM tool-calling and calls `interrupt()` to pause mid-node when a tool is needed. The interrupt return value carries the user's `approved` decision via `Command(resume=approved)`. A `tool_executor_node` calls the dummy microservices via httpx. `MemorySaver` checkpoints hold state between the `/chat` interrupt and the `/chat/tool-approval` resume. The frontend renders an approval card inline and disables input while pending.

**Tech Stack:** LangGraph 1.1.3 (MemorySaver, interrupt, Command), LangChain tool-calling (StructuredTool), httpx (async HTTP), FastAPI, React + TypeScript + Tailwind v4.

**Spec:** `docs/superpowers/specs/2026-03-20-tool-use-react-design.md`

---

## LangGraph Interrupt/Resume Pattern (Critical Context)

LangGraph 1.1.x uses `interrupt()` + `Command(resume=value)` for dynamic human-in-the-loop:

```python
# Inside a node — pauses graph, waits for resume value
from langgraph.types import interrupt
approved: bool = interrupt({"pending_tool_call": pending_info})
# When resumed with Command(resume=True), `approved` is True here
```

```python
# In the endpoint that resumes the graph:
from langgraph.types import Command
result = await graph.ainvoke(Command(resume=approved), config)
```

**Do NOT use** `aupdate_state + ainvoke(None)` for resuming from `interrupt()` — that pattern is for compile-time `interrupt_before=[...]` breakpoints only. Do **not** combine both patterns.

---

## File Map

### New Files
| File | Responsibility |
|---|---|
| `dummy_services/requirements.txt` | fastapi, uvicorn, pydantic |
| `dummy_services/main.py` | FastAPI app entry point, port 8001 |
| `dummy_services/routes/__init__.py` | Package marker |
| `dummy_services/routes/search.py` | POST /search — fake web search results |
| `dummy_services/routes/notify.py` | POST /notify — log & confirm notification |
| `dummy_services/routes/data.py` | POST /data — in-memory CRUD store |
| `backend/app/core/tools.py` | Tool registry: StructuredTool definitions + httpx executors |
| `backend/app/core/react_agent.py` | LangGraph ReAct graph with interrupt + MemorySaver |

### Modified Files
| File | Change |
|---|---|
| `backend/app/config.py` | Add `dummy_services_base_url` setting |
| `backend/app/schemas/chat.py` | Add `ToolCallInfo`, update `ChatResponse`, add `ToolApprovalRequest/Response` |
| `backend/app/api/v1/chat.py` | Swap rag_graph → react_agent, add `/tool-approval` endpoint |
| `backend/requirements.txt` | Add `httpx` |
| `frontend/src/api/chat.ts` | Add types + `approveToolCall()` function |
| `frontend/src/components/ChatWindow.tsx` | Render tool approval card for `pending_tool_approval` messages |
| `frontend/src/pages/ChatPage.tsx` | Handle pending state, thread_id, disable input, call approveToolCall |

---

## Task 1: Dummy Microservices App

**Files:**
- Create: `dummy_services/requirements.txt`
- Create: `dummy_services/main.py`
- Create: `dummy_services/routes/__init__.py`
- Create: `dummy_services/routes/search.py`
- Create: `dummy_services/routes/notify.py`
- Create: `dummy_services/routes/data.py`

- [ ] **Step 1.1: Create requirements.txt**

Create `dummy_services/requirements.txt`:
```
fastapi==0.135.1
uvicorn[standard]==0.42.0
pydantic==2.12.5
```

- [ ] **Step 1.2: Create routes package marker**

Create `dummy_services/routes/__init__.py` (empty file).

- [ ] **Step 1.3: Create search route**

Create `dummy_services/routes/search.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest):
    return SearchResponse(results=[
        SearchResult(
            title=f"Result 1 for: {body.query}",
            snippet=f"This is a fake snippet about '{body.query}'. Lorem ipsum dolor sit amet.",
            url="https://example.com/result-1",
        ),
        SearchResult(
            title=f"Result 2 for: {body.query}",
            snippet=f"Another fake result related to '{body.query}'. Consectetur adipiscing elit.",
            url="https://example.com/result-2",
        ),
        SearchResult(
            title=f"Result 3 for: {body.query}",
            snippet=f"Third fake result about '{body.query}'. Sed do eiusmod tempor incididunt.",
            url="https://example.com/result-3",
        ),
    ])
```

- [ ] **Step 1.4: Create notify route**

Create `dummy_services/routes/notify.py`:

```python
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class NotifyRequest(BaseModel):
    to: str
    message: str


class NotifyResponse(BaseModel):
    sent: bool
    to: str
    timestamp: str


@router.post("/notify", response_model=NotifyResponse)
def notify(body: NotifyRequest):
    print(f"[NOTIFY] To: {body.to} | Message: {body.message}")
    return NotifyResponse(
        sent=True,
        to=body.to,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

- [ ] **Step 1.5: Create data (CRUD) route**

Create `dummy_services/routes/data.py`:

```python
from typing import Any, Literal
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# In-memory store: {"resource_name": [item, ...]}
_store: dict[str, list[dict]] = {}


class DataRequest(BaseModel):
    action: Literal["create", "read", "update", "delete"]
    resource: str
    data: dict[str, Any] = {}


class DataResponse(BaseModel):
    success: bool
    action: str
    resource: str
    data: Any = None


@router.post("/data", response_model=DataResponse)
def data(body: DataRequest):
    store = _store.setdefault(body.resource, [])

    if body.action == "create":
        store.append(body.data)
        return DataResponse(success=True, action="create", resource=body.resource, data=body.data)

    if body.action == "read":
        return DataResponse(success=True, action="read", resource=body.resource, data=store)

    if body.action == "update":
        match_key = next(iter(body.data), None)
        if match_key is None:
            raise HTTPException(status_code=400, detail="data must contain at least one key to match")
        updated = False
        for item in store:
            if item.get(match_key) == body.data.get(match_key):
                item.update(body.data)
                updated = True
                break
        return DataResponse(success=updated, action="update", resource=body.resource, data=body.data)

    if body.action == "delete":
        match_key = next(iter(body.data), None)
        if match_key is None:
            raise HTTPException(status_code=400, detail="data must contain at least one key to match")
        before = len(store)
        _store[body.resource] = [i for i in store if i.get(match_key) != body.data.get(match_key)]
        deleted = before - len(_store[body.resource])
        return DataResponse(success=deleted > 0, action="delete", resource=body.resource, data={"deleted_count": deleted})

    raise HTTPException(status_code=400, detail=f"Unknown action: {body.action}")
```

- [ ] **Step 1.6: Create main.py**

Note: Import routes using `from routes import ...` (not `from dummy_services.routes import ...`) because uvicorn runs from inside the `dummy_services/` directory.

Create `dummy_services/main.py`:

```python
from fastapi import FastAPI
from routes import search, notify, data

app = FastAPI(title="Dummy Microservices", version="1.0.0")

app.include_router(search.router)
app.include_router(notify.router)
app.include_router(data.router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 1.7: Smoke test — start dummy services and hit each endpoint**

```bash
cd dummy_services
pip install -r requirements.txt
uvicorn main:app --port 8001
```

In another terminal:
```bash
curl -s -X POST http://localhost:8001/search -H "Content-Type: application/json" -d "{\"query\":\"test\"}"
curl -s -X POST http://localhost:8001/notify -H "Content-Type: application/json" -d "{\"to\":\"admin\",\"message\":\"hello\"}"
curl -s -X POST http://localhost:8001/data -H "Content-Type: application/json" -d "{\"action\":\"create\",\"resource\":\"users\",\"data\":{\"name\":\"Kevin\"}}"
curl -s -X POST http://localhost:8001/data -H "Content-Type: application/json" -d "{\"action\":\"read\",\"resource\":\"users\",\"data\":{}}"
```

Expected: all 4 return valid JSON responses.

- [ ] **Step 1.8: Commit**

```bash
git add dummy_services/
git commit -m "feat: add dummy microservices app (search, notify, crud)"
```

---

## Task 2: Backend Config & Schema Updates

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 2.1: Add `dummy_services_base_url` to config**

In `backend/app/config.py`, add one field after `chunk_overlap`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: Literal["openai", "gemini"] = "gemini"
    embedding_provider: Literal["google", "openai"] = "google"

    openai_api_key: str = ""
    google_api_key: str = ""

    chroma_persist_dir: str = "./data/chroma"
    collection_name: str = "generic_rag"
    top_k_results: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50
    dummy_services_base_url: str = "http://localhost:8001"


settings = Settings()
```

- [ ] **Step 2.2: Update schemas/chat.py**

Replace `backend/app/schemas/chat.py` entirely:

```python
from pydantic import BaseModel
from typing import Literal, Optional


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


class ToolApprovalRequest(BaseModel):
    thread_id: str
    session_id: str
    approved: bool


class ToolApprovalResponse(BaseModel):
    answer: str
    sources: list[SourceRef]
    session_id: str
    status: Literal["done", "pending_tool_approval"] = "done"
    pending_tool: Optional[ToolCallInfo] = None
    thread_id: Optional[str] = None
```

- [ ] **Step 2.3: Add httpx to backend requirements**

In `backend/requirements.txt`, add under `# Utilities`:
```
httpx==0.28.1
```

- [ ] **Step 2.4: Install httpx**

```bash
cd backend
pip install httpx==0.28.1
```

- [ ] **Step 2.5: Commit**

```bash
git add backend/app/config.py backend/app/schemas/chat.py backend/requirements.txt
git commit -m "feat: add tool-use schema types and config for dummy services URL"
```

---

## Task 3: Tool Registry & Executors

**Files:**
- Create: `backend/app/core/tools.py`
- Create: `backend/tests/test_tools.py`

Note: `StructuredTool` with async executors uses the `coroutine=` parameter (not `func=`). To invoke asynchronously, use `await tool.ainvoke({"param": value})` — do not call `.acoroutine()` directly.

- [ ] **Step 3.1: Write failing test**

Create `backend/tests/test_tools.py`:

```python
import pytest
import respx
import httpx


@respx.mock
@pytest.mark.asyncio
async def test_search_web_executor_success():
    """search_web_executor returns formatted results string"""
    respx.post("http://localhost:8001/search").mock(return_value=httpx.Response(200, json={
        "results": [
            {"title": "Test Title", "snippet": "Test snippet", "url": "https://example.com"}
        ]
    }))

    from app.core.tools import search_web_executor
    result = await search_web_executor(query="test query")
    assert "Test Title" in result
    assert "Test snippet" in result


@respx.mock
@pytest.mark.asyncio
async def test_search_web_executor_http_error():
    """search_web_executor returns error string on HTTP 500"""
    respx.post("http://localhost:8001/search").mock(return_value=httpx.Response(500))

    from app.core.tools import search_web_executor
    result = await search_web_executor(query="test")
    assert "error" in result.lower() or "failed" in result.lower() or "unavailable" in result.lower()


@respx.mock
@pytest.mark.asyncio
async def test_send_notification_executor_success():
    """send_notification_executor returns confirmation string"""
    respx.post("http://localhost:8001/notify").mock(return_value=httpx.Response(200, json={
        "sent": True, "to": "admin", "timestamp": "2026-01-01T00:00:00Z"
    }))

    from app.core.tools import send_notification_executor
    result = await send_notification_executor(to="admin", message="hello")
    assert "admin" in result
    assert "sent" in result.lower()


@respx.mock
@pytest.mark.asyncio
async def test_crud_data_executor_success():
    """crud_data_executor returns result string"""
    respx.post("http://localhost:8001/data").mock(return_value=httpx.Response(200, json={
        "success": True, "action": "create", "resource": "users", "data": {"name": "Kevin"}
    }))

    from app.core.tools import crud_data_executor
    result = await crud_data_executor(action="create", resource="users", data={"name": "Kevin"})
    assert "success" in result.lower() or "Kevin" in result
```

- [ ] **Step 3.2: Create requirements-dev.txt and install test dependencies**

Create `backend/requirements-dev.txt`:
```
respx==0.21.1
pytest-asyncio==0.24.0
pytest==8.3.5
```

```bash
cd backend
pip install -r requirements-dev.txt
```

- [ ] **Step 3.3: Run test to verify it fails**

```bash
cd backend
pytest tests/test_tools.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.core.tools` does not exist yet.

- [ ] **Step 3.4: Create tools.py**

Create `backend/app/core/tools.py`:

```python
import json
from typing import Literal
import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.config import settings


# --- Input schemas ---

class SearchWebInput(BaseModel):
    query: str


class SendNotificationInput(BaseModel):
    to: str
    message: str


class CRUDDataInput(BaseModel):
    action: Literal["create", "read", "update", "delete"]
    resource: str
    data: dict = {}


# --- Async executor functions ---

async def search_web_executor(query: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/search",
                json={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return "No results found."
            lines = [f"- {r['title']}: {r['snippet']} ({r['url']})" for r in results]
            return "\n".join(lines)
    except httpx.TimeoutException:
        return "Error: Search service timed out. Please try again."
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return f"Error: Search service unavailable (HTTP {e.response.status_code})."
        return f"Error: Invalid search request (HTTP {e.response.status_code})."
    except Exception as e:
        return f"Error: Search failed — {str(e)}"


async def send_notification_executor(to: str, message: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/notify",
                json={"to": to, "message": message},
            )
            resp.raise_for_status()
            data = resp.json()
            return f"Notification sent to '{data['to']}' at {data['timestamp']}."
    except httpx.TimeoutException:
        return "Error: Notification service timed out."
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return f"Error: Notification service unavailable (HTTP {e.response.status_code})."
        return f"Error: Invalid notification request (HTTP {e.response.status_code})."
    except Exception as e:
        return f"Error: Notification failed — {str(e)}"


async def crud_data_executor(action: str, resource: str, data: dict) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/data",
                json={"action": action, "resource": resource, "data": data},
            )
            resp.raise_for_status()
            result = resp.json()
            return f"Action '{action}' on '{resource}': success={result['success']}, data={json.dumps(result['data'])}"
    except httpx.TimeoutException:
        return "Error: Data service timed out."
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return f"Error: Data service unavailable (HTTP {e.response.status_code})."
        return f"Error: Invalid data request (HTTP {e.response.status_code})."
    except Exception as e:
        return f"Error: Data operation failed — {str(e)}"


# --- Tool registry ---
# Use coroutine= (not func=) for async tools in StructuredTool.
# Invoke via: await tool.ainvoke({"param": value})

TOOLS: list[StructuredTool] = [
    StructuredTool(
        name="search_web",
        description=(
            "Search the web for information about a topic or recent events. "
            "Use when the user asks about something not in the knowledge base."
        ),
        args_schema=SearchWebInput,
        coroutine=search_web_executor,
    ),
    StructuredTool(
        name="send_notification",
        description="Send a notification or message to a recipient.",
        args_schema=SendNotificationInput,
        coroutine=send_notification_executor,
    ),
    StructuredTool(
        name="crud_data",
        description=(
            "Create, read, update, or delete data in an external system. "
            "Action must be one of: create, read, update, delete."
        ),
        args_schema=CRUDDataInput,
        coroutine=crud_data_executor,
    ),
]
```

- [ ] **Step 3.5: Run tests**

```bash
cd backend
pytest tests/test_tools.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 3.6: Commit**

```bash
git add backend/app/core/tools.py backend/tests/test_tools.py
git commit -m "feat: add tool registry with search_web, send_notification, crud_data executors"
```

---

## Task 4: LangGraph ReAct Agent

**Files:**
- Create: `backend/app/core/react_agent.py`
- Create: `backend/tests/test_react_agent.py`

**Critical pattern — `interrupt()` + `Command(resume=)`:**
- `interrupt(payload)` pauses the graph mid-node and **returns** the value passed to `Command(resume=value)` when resumed
- Resume is done with `await graph.ainvoke(Command(resume=value), config)` — NOT `ainvoke(None)`
- Do NOT use `interrupt_before=[...]` in `graph.compile()` alongside `interrupt()` — pick one mechanism only

- [ ] **Step 4.1: Write failing test**

Create `backend/tests/test_react_agent.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import inspect


def test_run_agent_has_correct_signature():
    """run_agent and resume_agent exist with expected parameters"""
    from app.core.react_agent import run_agent, resume_agent

    run_sig = inspect.signature(run_agent)
    assert "message" in run_sig.parameters
    assert "history" in run_sig.parameters
    assert "session_id" in run_sig.parameters

    resume_sig = inspect.signature(resume_agent)
    assert "thread_id" in resume_sig.parameters
    assert "approved" in resume_sig.parameters
    assert "session_id" in resume_sig.parameters


@pytest.mark.asyncio
async def test_run_agent_returns_done_shape():
    """run_agent result dict has all required keys"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Paris is the capital of France."
    mock_response.tool_calls = []
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("app.core.react_agent.get_llm", return_value=mock_llm):
        # Re-import to pick up mock
        import importlib
        import app.core.react_agent as agent_module
        importlib.reload(agent_module)

        result = await agent_module.run_agent(
            message="What is the capital of France?",
            history=[],
            session_id="test-session",
        )

    assert "status" in result
    assert "answer" in result
    assert "sources" in result
    assert "thread_id" in result
    assert "pending_tool" in result
    assert "session_id" in result
```

- [ ] **Step 4.2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_react_agent.py::test_run_agent_has_correct_signature -v
```

Expected: `ImportError` — `app.core.react_agent` does not exist.

- [ ] **Step 4.3: Create react_agent.py**

Create `backend/app/core/react_agent.py`:

```python
import uuid
from typing import Annotated, Any

from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
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
    messages = []
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
    answer = final_message.content if hasattr(final_message, "content") else str(final_message)

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
    answer = final_message.content if hasattr(final_message, "content") else str(final_message)

    return {
        "status": "done",
        "answer": answer,
        "sources": result.get("sources", []),
        "thread_id": None,
        "pending_tool": None,
        "session_id": session_id,
    }
```

- [ ] **Step 4.4: Run tests**

```bash
cd backend
pytest tests/test_react_agent.py -v
```

Expected: both tests PASS (the signature test will pass immediately; the shape test will pass if LLM mock works).

- [ ] **Step 4.5: Commit**

```bash
git add backend/app/core/react_agent.py backend/tests/test_react_agent.py
git commit -m "feat: add LangGraph ReAct agent with interrupt/Command(resume) pattern"
```

---

## Task 5: Update Chat API Endpoints

**Files:**
- Modify: `backend/app/api/v1/chat.py`
- Create: `backend/tests/test_chat_api.py`

- [ ] **Step 5.1: Write failing test**

Create `backend/tests/test_chat_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


def make_client():
    from app.main import app
    return TestClient(app)


def test_chat_returns_done_status():
    """POST /chat returns status=done for a normal question"""
    mock_result = {
        "status": "done",
        "answer": "Paris is the capital of France.",
        "sources": [],
        "thread_id": None,
        "pending_tool": None,
        "session_id": "test-123",
    }
    with patch("app.api.v1.chat.run_agent", new=AsyncMock(return_value=mock_result)):
        client = make_client()
        resp = client.post("/api/v1/chat", json={"message": "Capital of France?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert "Paris" in data["answer"]


def test_chat_returns_pending_tool_approval():
    """POST /chat returns status=pending_tool_approval when tool is needed"""
    mock_result = {
        "status": "pending_tool_approval",
        "answer": "",
        "sources": [],
        "thread_id": "thread-abc",
        "pending_tool": {
            "tool_name": "search_web",
            "tool_args": {"query": "AI news"},
            "description": 'Searching web for: "AI news"',
        },
        "session_id": "test-123",
    }
    with patch("app.api.v1.chat.run_agent", new=AsyncMock(return_value=mock_result)):
        client = make_client()
        resp = client.post("/api/v1/chat", json={"message": "Search AI news"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending_tool_approval"
    assert data["thread_id"] == "thread-abc"
    assert data["pending_tool"]["tool_name"] == "search_web"


def test_tool_approval_approved():
    """POST /chat/tool-approval with approved=true returns final answer"""
    mock_result = {
        "status": "done",
        "answer": "Search results: ...",
        "sources": [],
        "thread_id": None,
        "pending_tool": None,
        "session_id": "test-123",
    }
    with patch("app.api.v1.chat.resume_agent", new=AsyncMock(return_value=mock_result)):
        client = make_client()
        resp = client.post("/api/v1/chat/tool-approval", json={
            "thread_id": "thread-abc",
            "session_id": "test-123",
            "approved": True,
        })
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


def test_tool_approval_stale_thread_returns_400():
    """POST /chat/tool-approval with stale thread_id returns 400"""
    with patch("app.api.v1.chat.resume_agent", new=AsyncMock(side_effect=ValueError("No pending approval"))):
        client = make_client()
        resp = client.post("/api/v1/chat/tool-approval", json={
            "thread_id": "stale-thread",
            "session_id": "test-123",
            "approved": True,
        })
    assert resp.status_code == 400
    assert "expired" in resp.json()["detail"].lower() or "pending" in resp.json()["detail"].lower()
```

- [ ] **Step 5.2: Run tests to verify they fail**

```bash
cd backend
pytest tests/test_chat_api.py -v
```

Expected: tests fail because `chat.py` still imports `rag_graph` (which exists), but `run_agent` / `resume_agent` are not imported.

- [ ] **Step 5.3: Replace chat.py**

Replace `backend/app/api/v1/chat.py` entirely:

```python
import uuid
from fastapi import APIRouter, HTTPException

from app.schemas.chat import (
    ChatRequest, ChatResponse,
    ToolApprovalRequest, ToolApprovalResponse,
    SourceRef, ToolCallInfo,
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
```

- [ ] **Step 5.4: Run tests**

```bash
cd backend
pytest tests/test_chat_api.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5.5: Run full test suite**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 5.6: Commit**

```bash
git add backend/app/api/v1/chat.py backend/tests/test_chat_api.py
git commit -m "feat: update chat endpoints to use ReAct agent with tool approval flow"
```

---

## Task 6: Frontend — Types & API

**Files:**
- Modify: `frontend/src/api/chat.ts`

- [ ] **Step 6.1: Update chat.ts**

Replace `frontend/src/api/chat.ts`:

```typescript
import api from './client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface SourceRef {
  doc_id: string
  title: string
  excerpt: string
}

export interface ToolCallInfo {
  tool_name: string
  tool_args: Record<string, unknown>
  description: string
}

export interface ChatRequest {
  message: string
  session_id?: string
  history?: ChatMessage[]
  strict_mode?: boolean
}

export interface ChatResponse {
  answer: string
  sources: SourceRef[]
  session_id: string
  status: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
}

export interface ToolApprovalRequest {
  thread_id: string
  session_id: string
  approved: boolean
}

export interface ToolApprovalResponse {
  answer: string
  sources: SourceRef[]
  session_id: string
  status: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
}

export async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>('/chat', req)
  return data
}

export async function approveToolCall(req: ToolApprovalRequest): Promise<ToolApprovalResponse> {
  const { data } = await api.post<ToolApprovalResponse>('/chat/tool-approval', req)
  return data
}
```

- [ ] **Step 6.2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1
```

Expected: no TypeScript errors related to `chat.ts`.

- [ ] **Step 6.3: Commit**

```bash
git add frontend/src/api/chat.ts
git commit -m "feat: add ToolCallInfo types and approveToolCall API function"
```

---

## Task 7: Frontend — ChatWindow Tool Approval Card

**Files:**
- Modify: `frontend/src/components/ChatWindow.tsx`

- [ ] **Step 7.1: Update ChatWindow.tsx**

Replace `frontend/src/components/ChatWindow.tsx`:

```tsx
import { useEffect, useRef } from 'react'
import type { ChatMessage, SourceRef, ToolCallInfo } from '../api/chat'

export interface DisplayMessage extends ChatMessage {
  sources?: SourceRef[]
  status?: 'done' | 'pending_tool_approval'
  pending_tool?: ToolCallInfo
  thread_id?: string
}

interface Props {
  messages: DisplayMessage[]
  loading: boolean
  onApprove?: (threadId: string) => void
  onCancel?: (threadId: string) => void
}

function SourcesBlock({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null
  return (
    <details className="mt-2 text-xs">
      <summary className="cursor-pointer text-indigo-500 hover:text-indigo-700 font-medium select-none">
        {sources.length} source{sources.length > 1 ? 's' : ''}
      </summary>
      <ul className="mt-2 space-y-2">
        {sources.map(src => (
          <li key={src.doc_id} className="rounded-lg bg-indigo-50 px-3 py-2">
            <p className="font-semibold text-indigo-700">{src.title}</p>
            <p className="text-gray-500 mt-0.5 line-clamp-2">{src.excerpt}</p>
          </li>
        ))}
      </ul>
    </details>
  )
}

function ToolApprovalCard({
  pending_tool,
  thread_id,
  onApprove,
  onCancel,
}: {
  pending_tool: ToolCallInfo
  thread_id: string
  onApprove: (id: string) => void
  onCancel: (id: string) => void
}) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm shadow-sm max-w-[75%]">
      <p className="font-semibold text-amber-800 mb-1">🔧 System wants to run a tool:</p>
      <p className="font-mono text-amber-900 text-xs mb-0.5">{pending_tool.tool_name}</p>
      <p className="text-amber-700 text-xs mb-3">→ {pending_tool.description}</p>
      <div className="flex gap-2">
        <button
          onClick={() => onApprove(thread_id)}
          className="px-3 py-1.5 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700 cursor-pointer transition-colors"
        >
          ✓ Approve
        </button>
        <button
          onClick={() => onCancel(thread_id)}
          className="px-3 py-1.5 rounded-lg bg-gray-200 text-gray-700 text-xs font-medium hover:bg-gray-300 cursor-pointer transition-colors"
        >
          ✗ Cancel
        </button>
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, loading, onApprove, onCancel }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  if (!messages.length && !loading) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
        Ask a question based on your knowledge base.
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
      {messages.map((msg, i) => {
        if (msg.role === 'assistant' && msg.status === 'pending_tool_approval' && msg.pending_tool && msg.thread_id) {
          return (
            <div key={i} className="flex justify-start">
              <ToolApprovalCard
                pending_tool={msg.pending_tool}
                thread_id={msg.thread_id}
                onApprove={onApprove ?? (() => {})}
                onCancel={onCancel ?? (() => {})}
              />
            </div>
          )
        }

        return (
          <div
            key={i}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
                msg.role === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-sm'
                  : 'bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.role === 'assistant' && msg.sources && (
                <SourcesBlock sources={msg.sources} />
              )}
            </div>
          </div>
        )
      })}
      {loading && (
        <div className="flex justify-start">
          <div className="max-w-[75%] rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-3 shadow-sm">
            <div className="flex gap-1 items-center h-4">
              <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:0ms]" />
              <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:150ms]" />
              <span className="w-2 h-2 rounded-full bg-gray-300 animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 7.2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1
```

Expected: no TypeScript errors.

- [ ] **Step 7.3: Commit**

```bash
git add frontend/src/components/ChatWindow.tsx
git commit -m "feat: add tool approval card to ChatWindow"
```

---

## Task 8: Frontend — ChatPage Approval Logic

**Files:**
- Modify: `frontend/src/pages/ChatPage.tsx`

- [ ] **Step 8.1: Update ChatPage.tsx**

Replace `frontend/src/pages/ChatPage.tsx`:

```tsx
import { useState } from 'react'
import { sendMessage, approveToolCall } from '../api/chat'
import ChatWindow from '../components/ChatWindow'
import type { DisplayMessage } from '../components/ChatWindow'
import ChatInput from '../components/ChatInput'

export default function ChatPage() {
  const [messages, setMessages] = useState<DisplayMessage[]>([])
  const [sessionId, setSessionId] = useState<string | undefined>()
  const [loading, setLoading] = useState(false)
  const [strictMode, setStrictMode] = useState(true)
  // pendingApproval: true while waiting for user to approve/cancel a tool
  const [pendingApproval, setPendingApproval] = useState(false)

  async function handleSend(text: string) {
    const userMsg: DisplayMessage = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      // Exclude approval card messages from history sent to backend
      const history = messages
        .filter(m => m.status !== 'pending_tool_approval')
        .map(m => ({ role: m.role, content: m.content }))

      const res = await sendMessage({
        message: text,
        session_id: sessionId,
        history,
        strict_mode: strictMode,
      })
      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            status: 'pending_tool_approval',
            pending_tool: res.pending_tool,
            thread_id: res.thread_id,
          },
        ])
        setPendingApproval(true)
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
        ])
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleApprove(threadId: string) {
    if (!sessionId) return
    setPendingApproval(false)
    setLoading(true)

    // Replace approval card with executing status
    setMessages(prev =>
      prev.map(m =>
        m.thread_id === threadId
          ? { ...m, content: '⏳ Executing tool...', status: 'done' as const, pending_tool: undefined }
          : m
      )
    )

    try {
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: true })
      setSessionId(res.session_id)

      if (res.status === 'pending_tool_approval') {
        // Another tool call in the loop
        setMessages(prev => [
          ...prev,
          {
            role: 'assistant',
            content: '',
            status: 'pending_tool_approval',
            pending_tool: res.pending_tool,
            thread_id: res.thread_id,
          },
        ])
        setPendingApproval(true)
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
        ])
      }
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Tool execution failed. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function handleCancel(threadId: string) {
    if (!sessionId) return
    setPendingApproval(false)
    setLoading(true)

    // Replace approval card with cancelled status
    setMessages(prev =>
      prev.map(m =>
        m.thread_id === threadId
          ? { ...m, content: '✗ Tool execution cancelled.', status: 'done' as const, pending_tool: undefined }
          : m
      )
    )

    try {
      const res = await approveToolCall({ thread_id: threadId, session_id: sessionId, approved: false })
      setSessionId(res.session_id)
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources, status: 'done' },
      ])
    } catch {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: 'Something went wrong after cancellation. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleNewChat() {
    setMessages([])
    setSessionId(undefined)
    setPendingApproval(false)
  }

  // Disable input both while loading AND while waiting for tool approval
  const inputDisabled = loading || pendingApproval

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 flex flex-col h-screen">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chat</h1>
          <p className="text-sm text-gray-500">Ask questions based on your knowledge base.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className={`flex items-center gap-2 text-sm border rounded-lg px-3 py-1.5 cursor-pointer transition-colors ${
              strictMode
                ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                : 'bg-gray-50 border-gray-200 text-gray-500'
            }`}
            onClick={() => setStrictMode(prev => !prev)}
            title={strictMode ? 'Strict: hanya jawab dari knowledge base' : 'Bebas: boleh jawab dari general knowledge'}
          >
            {strictMode ? '🔒 Strict' : '💬 Bebas'}
          </button>
          {messages.length > 0 && (
            <button
              className="text-sm text-gray-400 hover:text-gray-600 border border-gray-200 rounded-lg px-3 py-1.5 cursor-pointer"
              onClick={handleNewChat}
            >
              New chat
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col flex-1 rounded-2xl border border-gray-200 bg-gray-50 overflow-hidden shadow-sm">
        <ChatWindow
          messages={messages}
          loading={loading}
          onApprove={handleApprove}
          onCancel={handleCancel}
        />
        <ChatInput onSend={handleSend} disabled={inputDisabled} />
      </div>
    </div>
  )
}
```

- [ ] **Step 8.2: Verify TypeScript compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1
```

Expected: no TypeScript errors.

- [ ] **Step 8.3: Commit**

```bash
git add frontend/src/pages/ChatPage.tsx
git commit -m "feat: add tool approval/cancel handling to ChatPage"
```

---

## Task 9: Update Architecture Decisions

**Files:**
- Modify: `.claude/decisions.md`

- [ ] **Step 9.1: Append ADR-005 and ADR-006 to decisions.md**

Open `c:/Kevin/Github/generic-rag/.claude/decisions.md` and append:

```markdown
## ADR-005 — MemorySaver untuk interrupt state (2026-03-20)

**Decision:** Gunakan `MemorySaver` (in-memory) dari LangGraph untuk menyimpan graph state saat interrupt.

**Reasoning:** `thread_id` hanya hidup selama satu approval cycle (beberapa detik antara `/chat` dan `/chat/tool-approval`). Tidak perlu database persisten untuk ini di MVP.

**Trade-off:** Pending approval hilang jika backend restart. Frontend handle HTTP 400 dan inform user untuk kirim ulang. Jika persistence diperlukan di masa depan, ganti `MemorySaver` dengan `SqliteSaver` atau `PostgresSaver` — tidak ada perubahan logika lain.

## ADR-006 — Dummy microservices sebagai app terpisah (2026-03-20)

**Decision:** Dummy services di-deploy sebagai FastAPI app terpisah di `dummy_services/` (port 8001), bukan endpoint di backend utama.

**Reasoning:** Mensimulasikan deployment separation yang nyata. Saat microservices asli bisa diakses, cukup ganti `DUMMY_SERVICES_BASE_URL` di `backend/.env`.

**Migration:** `DUMMY_SERVICES_BASE_URL=https://real-service.internal` di `backend/.env`.
```

- [ ] **Step 9.2: Commit**

```bash
git add .claude/decisions.md
git commit -m "docs: add ADR-005 (MemorySaver) and ADR-006 (dummy microservices)"
```

---

## Task 10: End-to-End Verification

- [ ] **Step 10.1: Run all backend tests**

```bash
cd backend
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 10.2: Start all 3 services**

Terminal 1 — dummy services:
```bash
cd dummy_services
uvicorn main:app --port 8001
```

Terminal 2 — backend:
```bash
cd backend
uvicorn app.main:app --port 8000 --reload
```

Terminal 3 — frontend:
```bash
cd frontend
npm run dev
```

- [ ] **Step 10.3: Test — RAG / direct answer (no tool)**

Open `http://localhost:5173`. Send: `"What is 2 + 2?"`

Expected:
- No approval card appears
- Normal assistant response
- `status: "done"` in network tab response

- [ ] **Step 10.4: Test — Tool approve flow**

Send: `"Search the web for latest AI news"`

Expected:
- Approval card: "🔧 System wants to run a tool: search_web → Searching web for: ..."
- ChatInput is disabled (cannot type)
- Click "✓ Approve"
- Card replaced with "⏳ Executing tool..."
- Final response with fake search results from dummy service

- [ ] **Step 10.5: Test — Tool cancel flow**

Send: `"Send a notification to admin"`

Expected:
- Approval card for `send_notification`
- Click "✗ Cancel"
- Card replaced with "✗ Tool execution cancelled."
- LLM asks user what went wrong

- [ ] **Step 10.6: Test — CRUD tool**

Send: `"Save new data: name Kevin, role engineer"`

Expected:
- Approval card for `crud_data` with action=create
- Approve → confirmation response

- [ ] **Step 10.7: Test — Dummy service down**

Stop dummy_services (`Ctrl+C` in Terminal 1). Send: `"Search for Python news"`

Expected:
- Approval card appears → Approve
- Error message in chat (not a crash): "Error: Search service timed out" or similar

- [ ] **Step 10.8: Test — Stale approval (HTTP 400)**

Open browser devtools network tab. Send a message that triggers tool approval. Before clicking Approve/Cancel, manually send a `POST /api/v1/chat/tool-approval` with a fake `thread_id`.

Expected: HTTP 400 with `"Tool approval expired or not found"` in detail.

- [ ] **Step 10.9: Final commit**

```bash
git add .
git commit -m "feat: complete tool use ReAct system with human-in-the-loop approval"
```
